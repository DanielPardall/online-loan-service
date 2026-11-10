from django.shortcuts import render
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
import os
from django.conf import settings
import json
import boto3
import logging
import time
import json
from botocore.exceptions import ClientError
from api.decorators import allowed_users, admin_only

from .serializers import (
    UserRegisterSerializer,
    UserSerializer,
    GroupSerializer,
    CustomTokenObtainPairSerializer,
)


# ---- REGISTER VIEW ---- #
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Endpoint para registrar um novo utilizador.
    """
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Utilizador registado com sucesso!", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )
    return Response(
        {"errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )


# ---- CUSTOM TOKEN OBTAIN PAIR ---- #
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Retorna access e refresh tokens para autenticação JWT.
    """
    serializer_class = CustomTokenObtainPairSerializer

# ---- USER VIEWS ---- #
class CreateUserView(generics.CreateAPIView):
    """
    Classe para registrar utilizadores com base na API REST.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


# ---- AUTHENTICATION CHECK ---- #
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def is_logged_in(request):
    """
    Endpoint para verificar se o utilizador está autenticado.
    """
    return Response({'authenticated': True, 'user': request.user.username})


# ---- LOGOUT ---- #
@api_view(['POST'])
def logout(request):
    """
    Endpoint para apagar cookies de tokens (logout).
    """
    response = Response({"message": "Logout realizado com sucesso!"})
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


# ---- LOAN APPLICATION ---- #
stepfunctions_client = boto3.client(
    'stepfunctions',
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    aws_session_token=settings.AWS_SESSION_TOKEN
)

logger = logging.getLogger(__name__)

import boto3
from datetime import datetime
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from botocore.exceptions import ClientError
from django.conf import settings


dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
table = dynamodb.Table(settings.DYNAMODB_TABLE)

class StartLoanWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Valida e extrai os dados necessários
            required_fields = ["amount", "duration", "income"]
            for field in required_fields:
                if field not in request.data or not request.data[field]:
                    return Response(
                        {"error": f"O campo '{field}' é obrigatório."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            timestamp = datetime.utcnow().isoformat()

            # Input para a Step Function
            step_function_input = {
                "amount": float(request.data["amount"]),
                "duration": int(request.data["duration"]),
                "income": float(request.data["income"]),
                "email": request.user.email,
                "timestamp": timestamp
            }

            # Inicia a Step Function
            execution_response = stepfunctions_client.start_execution(
                stateMachineArn=settings.STEP_FUNCTION_ARN,
                input=json.dumps(step_function_input),
            )

            execution_arn = execution_response["executionArn"]

            # Retorna o executionArn e timestamp
            return Response({"executionArn": execution_arn, "timestamp": timestamp}, status=status.HTTP_200_OK)

        except ClientError as e:
            return Response(
                {"error": "Erro ao iniciar o workflow.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": "Erro inesperado.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CheckLoanWorkflowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        execution_arn = request.query_params.get("executionArn")
        if not execution_arn:
            return Response(
                {"error": "O parâmetro 'executionArn' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            while True:
                # Consulta o status do workflow
                execution_result = stepfunctions_client.describe_execution(
                    executionArn=execution_arn
                )
                status_execution = execution_result["status"]

                # Verifica se o workflow foi concluído
                if status_execution in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
                    break

                # Aguarde 2 segundos antes de consultar novamente
                time.sleep(2)

            if status_execution == "SUCCEEDED":
                output = json.loads(execution_result["output"])
                return Response(output, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "error": "Workflow falhou ou não foi concluído com sucesso.",
                        "status": status_execution,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except ClientError as e:
            return Response(
                {"error": "Erro ao verificar o status do workflow.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": "Erro inesperado.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---- STATIC RENDER VIEWS ---- #
def react_app(request):
    return render(request, 'index.html')


def landing_page(request):
    return render(request, 'landing_page.html')

# ------------------- frontend 2 ---------
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
table = dynamodb.Table(settings.DYNAMODB_TABLE)

def get_completed_loans():
    """Obtém empréstimos com estado 'Aprovado' ou 'Rejeitado'."""
    response = table.scan(
        FilterExpression=Attr('Estado').eq('Aprovado') | Attr('Estado').eq('Rejeitado')
    )
    loans = response.get('Items', [])
    # Normalizar os dados para o frontend
    normalized_loans = [
        {
            "email": loan.get("email"),
            "timestamp": loan.get("timestamp"),
            "pontuacao_credito": float(loan.get("PontuacaoCredito", 0)),
            "classificacao_automatica": loan.get("ClassificacaoAutomatica"),
            "estado": loan.get("Estado"),
        }
        for loan in loans
    ]
    return normalized_loans

def get_pending_loans():
    """Obtém empréstimos com estado 'Por Analisar' ou 'Aguardar Entrevista'."""
    response = table.scan(
        FilterExpression=Attr('Estado').eq('Por Analisar') | Attr('Estado').eq('Aguardar Entrevista')
    )
    items = response.get('Items', [])
    
    # Mapear os campos para os nomes esperados pelo frontend
    mapped_items = [
        {
            "email": item.get("email"),
            "timestamp": item.get("timestamp"),
            "valor_emprestimo": float(item.get("ValorEmprestimo", 0)),
            "duracao": int(item.get("Duracao", 0)),
            "renda_mensal": float(item.get("RendaMensal", 0)),
            "pontuacao_credito": float(item.get("PontuacaoCredito", 0)),
            "classificacao_automatica": item.get("ClassificacaoAutomatica"),
            "estado": item.get("Estado"),
        }
        for item in items
    ]
    return mapped_items

# Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@allowed_users(allowed_roles=['gerentes'])
@admin_only
def get_completed_loans_view(request):
    """API para obter empréstimos concluídos."""
    try:
        completed_loans = get_completed_loans()
        return Response(completed_loans, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@allowed_users(allowed_roles=['gerentes'])
@admin_only
def get_pending_loans_view(request):
    pending_loans = get_pending_loans()
    return Response(pending_loans, status=status.HTTP_200_OK)

def get_loan_by_id(email, timestamp):
    """Obtém um empréstimo específico com base no email e timestamp."""
    response = table.query(
        KeyConditionExpression=Key('email').eq(email) & Key('timestamp').eq(timestamp)
    )
    if response['Items']:
        item = response['Items'][0]
        return {
            "email": item.get("email"),
            "timestamp": item.get("timestamp"),
            "valor_emprestimo": float(item.get("ValorEmprestimo", 0)),
            "duracao": int(item.get("Duracao", 0)),
            "renda_mensal": float(item.get("RendaMensal", 0)),
            "pontuacao_credito": float(item.get("PontuacaoCredito", 0)),
            "classificacao_automatica": item.get("ClassificacaoAutomatica"),
            "estado": item.get("Estado"),
            "entrevista_datas": item.get("DatasEntrevista", []),
        }
    return None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@allowed_users(allowed_roles=['gerentes'])
@admin_only
def get_loan_details_view(request, email, timestamp):
    """Obtém os detalhes de um empréstimo."""
    loan = get_loan_by_id(email, timestamp)
    if loan:
        return Response(loan, status=status.HTTP_200_OK)
    return Response({"error": "Empréstimo não encontrado."}, status=status.HTTP_404_NOT_FOUND)


def update_loan(email, timestamp, estado, entrevista_datas=None):
    """Atualiza o estado do empréstimo e define as datas de entrevista, se aplicável."""
    update_expression = "SET Estado = :estado"
    expression_attribute_values = {":estado": estado}

    if entrevista_datas:
        update_expression += ", DatasEntrevista = :datas"
        expression_attribute_values[":datas"] = entrevista_datas

    response = table.update_item(
        Key={"email": email, "timestamp": timestamp},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="UPDATED_NEW",
    )
    return response

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_loan_view(request, email, timestamp):
    """Atualiza os detalhes de um empréstimo."""
    data = request.data
    novo_estado = data.get("estado")
    entrevista_datas = data.get("entrevista_datas", None)

    # Validação obrigatória das datas
    if novo_estado in ["Aguardar Entrevista", "Entrevista"] and (not entrevista_datas or len(entrevista_datas) == 0):
        return Response(
            {"error": "É necessário fornecer pelo menos uma data para a entrevista."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Atualiza o estado
    response = update_loan(email, timestamp, novo_estado, entrevista_datas)
    return Response({"message": "Empréstimo atualizado com sucesso!", "response": response}, status=status.HTTP_200_OK)


class MonitorLoanStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            email = request.user.email
            timestamp = request.query_params.get("timestamp")

            logger.info(f"[MonitorLoanStatus] Iniciando verificação - Email: {email}, Timestamp: {timestamp}")

            if not timestamp:
                logger.warning("[MonitorLoanStatus] Timestamp ausente na requisição")
                return Response(
                    {"error": "O parâmetro 'timestamp' é obrigatório."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            while True:
                logger.info(f"[MonitorLoanStatus] Consultando DynamoDB - Key: {{'email': {email}, 'timestamp': {timestamp}}}")

                # Consulta o DynamoDB para obter o pedido
                response = table.get_item(
                    Key={"email": email, "timestamp": timestamp}
                )

                if "Item" not in response:
                    logger.warning(f"[MonitorLoanStatus] Pedido não encontrado no DynamoDB - Email: {email}, Timestamp: {timestamp}")
                    return Response(
                        {"error": "Pedido não encontrado."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                pedido = response["Item"]
                estado = pedido.get("Estado")
                logger.info(f"[MonitorLoanStatus] Pedido encontrado - Estado: {estado}")

                # Verifica o estado e decide a resposta
                if estado == "Por Analisar":
                    logger.info(f"[MonitorLoanStatus] Estado atual: Por Analisar. Aguardando 2 segundos para nova tentativa.")
                    time.sleep(2)
                    continue
                elif estado in ["Aprovado", "Rejeitado"]:
                    logger.info(f"[MonitorLoanStatus] Estado final alcançado: {estado}")
                    return Response({"message": f"Pedido {estado}."}, status=status.HTTP_200_OK)
                elif estado == "Aguardar Entrevista":
                    datas_entrevista = pedido.get("DatasEntrevista", [])
                    logger.info(f"[MonitorLoanStatus] Aguardando entrevista. Datas disponíveis: {datas_entrevista}")
                    return Response(
                        {"message": "Aguardando entrevista.", "DatasEntrevista": datas_entrevista},
                        status=status.HTTP_200_OK,
                    )
                else:
                    logger.warning(f"[MonitorLoanStatus] Estado desconhecido: {estado}")
                    return Response({"message": "Estado desconhecido."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"[MonitorLoanStatus] Erro inesperado: {str(e)}")
            return Response(
                {"error": "Erro ao consultar o status do pedido.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class UpdateClientChoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            email = request.data.get("email")
            timestamp = request.data.get("timestamp")
            escolha_cliente = request.data.get("escolha_cliente")

            logger.info(f"[UpdateClientChoice] Requisição recebida - Email: {email}, Timestamp: {timestamp}, Escolha: {escolha_cliente}")

            if not timestamp or not escolha_cliente:
                logger.warning("[UpdateClientChoice] Campos obrigatórios ausentes")
                return Response(
                    {"error": "Os campos 'timestamp' e 'escolha_cliente' são obrigatórios."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Atualiza o campo escolha_cliente no DynamoDB
            logger.info(f"[UpdateClientChoice] Atualizando DynamoDB - Chave: {{'email': {email}, 'timestamp': {timestamp}}}, Escolha: {escolha_cliente}")

            response = table.update_item(
                Key={"email": email, "timestamp": timestamp},
                UpdateExpression="SET escolha_cliente = :escolha",
                ExpressionAttributeValues={":escolha": escolha_cliente},
                ReturnValues="ALL_NEW",  # Retorna os valores atualizados
            )

            updated_attributes = response.get("Attributes", {})
            logger.info(f"[UpdateClientChoice] Resposta do DynamoDB: {updated_attributes}")

            if not updated_attributes or updated_attributes.get("escolha_cliente") != escolha_cliente:
                logger.error("[UpdateClientChoice] Atualização falhou ou inconsistência detectada no DynamoDB.")
                return Response(
                    {"error": "Falha ao atualizar a escolha do cliente no DynamoDB."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(f"[UpdateClientChoice] Atualização bem-sucedida: {updated_attributes}")

            return Response(
                {"message": "Escolha do cliente atualizada com sucesso.", "updated": updated_attributes},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"[UpdateClientChoice] Erro inesperado: {str(e)}")
            return Response(
                {"error": "Erro ao atualizar a escolha do cliente.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )




class MonitorFinalDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            email = request.query_params.get("email")
            timestamp = request.query_params.get("timestamp")

            logger.info(f"[MonitorFinalDecision] Iniciando monitoramento - Email: {email}, Timestamp: {timestamp}")

            if not timestamp:
                logger.warning("[MonitorFinalDecision] Timestamp ausente na requisição")
                return Response(
                    {"error": "O parâmetro 'timestamp' é obrigatório."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            while True:
                logger.info(f"[MonitorFinalDecision] Consultando DynamoDB - Key: {{'email': {email}, 'timestamp': {timestamp}}}")

                response = table.get_item(
                    Key={"email": email, "timestamp": timestamp}
                )

                if "Item" not in response:
                    logger.warning(f"[MonitorFinalDecision] Pedido não encontrado no DynamoDB - Email: {email}, Timestamp: {timestamp}")
                    return Response(
                        {"error": "Pedido não encontrado."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                pedido = response["Item"]
                estado = pedido.get("Estado")
                logger.info(f"[MonitorFinalDecision] Pedido encontrado - Estado: {estado}")

                if estado in ["Aprovado", "Rejeitado"]:
                    logger.info(f"[MonitorFinalDecision] Estado final alcançado: {estado}")
                    return Response({"message": f"Pedido {estado}."}, status=status.HTTP_200_OK)

                logger.info(f"[MonitorFinalDecision] Estado atual: {estado}. Aguardando 2 segundos para nova tentativa.")
                time.sleep(2)

        except Exception as e:
            logger.error(f"[MonitorFinalDecision] Erro inesperado: {str(e)}")
            return Response(
                {"error": "Erro ao consultar o status do pedido.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )





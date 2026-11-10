# Frontend source status

This folder preserves the React/Vite package manifest, lockfile and configuration supplied with the project.

**The supplied archive does not contain `src/` or the `/src/main.jsx` entry point referenced in `index.html`.** Running `npm run dev` or `npm run build` will not produce the original application until these sources are restored.

The generated JavaScript/CSS bundle previously copied to the backend was excluded from this source-oriented package. It cannot replace maintainable React source. No missing UI has been fabricated.

Restore the original frontend sources here, verify the API base URL in that source, then use `npm ci` and `npm run dev`. See the root README for the backend and AWS dependencies.

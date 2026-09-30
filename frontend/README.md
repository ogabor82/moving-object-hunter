# Moving Object Hunter – frontend

React + Vite + TypeScript frontend with a typed client for the backend API
(`src/api/`). AS-029: a blink comparator for real ZTF frame cutouts of the
frozen validation sequences (`src/components/BlinkComparator.tsx`), plus
the backend connection status.

```
npm install
npm run dev        # http://localhost:5173, proxies /api to the backend
npm run build      # type-check (tsc -b) and production build
npm run lint       # oxlint
```

The dev server forwards `/api/*` to `http://127.0.0.1:8000` (override with
`BACKEND_URL=... npm run dev`). Start the backend first; see the repository
README.

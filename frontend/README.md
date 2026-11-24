# Marmotte : le front

L'app des parents, installée sur l'écran d'accueil des téléphones (PWA) : React 19, TypeScript, Vite. Aujourd'hui, c'est un squelette qui affiche « Marmotte » ; il n'appelle pas encore le back. Les écrans (état, live, modes, notifications) arrivent avec le lot 6 (`docs/plans/`).

## Prérequis

- **Node.js 24**, installé de préférence avec [nvm](https://github.com/nvm-sh/nvm), qui lit la version dans `.nvmrc` :

```bash
cd frontend
nvm install   # une fois
nvm use       # à chaque nouveau terminal
```

## Installation

```bash
npm ci
```

`npm ci` installe les dépendances aux versions exactes de `package-lock.json`.

## Lancer en développement

```bash
npm run dev
```

L'app s'ouvre sur <http://localhost:5173> et se recharge à chaque modification.

## Tests et qualité

```bash
npx vitest --run       # tests (npm test : en continu, à chaque modification)
npm run lint           # ESLint
npm run typecheck      # types (TypeScript)
npm run format:check   # mise en forme (Prettier) ; npm run format pour corriger
```

Depuis la racine du dépôt, `just lint` et `just test` lancent tout, back et front.

## Construire

```bash
npm run build     # produit dist/
npm run preview   # sert dist/ en local, pour vérifier
```

## Organisation

```
frontend/
  index.html          page d'entrée (lang="fr")
  src/
    main.tsx          démarre React
    App.tsx           l'app
    App.test.tsx      ses tests (Vitest, Testing Library)
  vitest.setup.ts     ajoute les vérifications de Testing Library aux tests
  vite.config.ts      réglages de Vite et de Vitest
  eslint.config.js, .prettierrc, tsconfig*.json
```

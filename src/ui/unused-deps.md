# Depcheck: Unused & Missing Dependencies Review

This file was generated from `depcheck` output (`depcheck.json`). Use it to review and act later.

## Unused runtime dependencies (candidates for removal)

- @fontsource/roboto
- dotenv
- fast-is-equal
- path
- rc-tooltip
- react-paginate
- react-query
- recompose

## Unused devDependencies (candidates for removal)

- @chromatic-com/storybook
- @storybook/addon-essentials
- @storybook/addon-onboarding
- @storybook/blocks
- @storybook/react-vite
- @testing-library/react
- @testing-library/user-event
- @types/react-dom
- @vitest/coverage-v8
- identity-obj-proxy
- jest-environment-jsdom
- playwright
- prop-types
- vite-tsconfig-paths

Note: Some Storybook/test deps are expected for CI or developer UX — confirm before removing.

## Missing (used in code but not declared)

- @storybook/addon-actions — referenced by `src/components/UIElements/TableComponent/TableComponent.stories.jsx`
- redux — referenced by `src/app/store/reducers.js`
- reselect — referenced by `src/app/store/config/selectors/uiStateSelectors.js`

## Observations from depcheck

- Packages still observed in codebase and likely required: axios, @reduxjs/toolkit, react-redux, @mui/\*, d3, papaparse, xlsx, uuid, @mui/x-data-grid, react-router-dom, redux-persist, etc.
- `axios` appears only in `src/app/store/api.js` (RTK Query uses axios baseQuery). If you remove `axios`, ensure to replace `axiosBaseQuery` or switch to `fetchBaseQuery`.

## Recommended next steps

1. Add missing deps to `src/ui/package.json` (`redux`, `reselect`, `@storybook/addon-actions`) or update imports to avoid requiring them.
2. Remove unused runtime deps from `package.json` after manual verification and run `npm install`.
3. Keep or prune dev deps only after confirming Storybook and test needs. Consider running Storybook and tests locally before removal.
4. Add a CI lint rule (post-cleanup) to prevent reintroducing unused runtime deps.

If you want, I can prepare a `package.json` patch removing the runtime deps and adding the missing ones, and run `npm install` in `src/ui`.

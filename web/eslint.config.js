import js from '@eslint/js'
import globals from 'globals'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

/** An app or the shared package may import another part only through its package name. */
const boundaries = (forbidden) => ({
  'no-restricted-imports': [
    'error',
    {
      patterns: [
        {
          group: forbidden,
          message:
            'Share code through @epm2mod/ui (its index.ts): an app never imports another app, and the shared package never imports an app.',
        },
        {
          group: ['@epm2mod/ui/src/*', '**/packages/ui/**'],
          message: "Import from '@epm2mod/ui'; add the export to packages/ui/src/index.ts if it is missing.",
        },
      ],
    },
  ],
})

export default tseslint.config(
  { ignores: ['**/dist', '**/node_modules', '**/test-results'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      jsxA11y.flatConfigs.recommended,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
  { files: ['packages/ui/**/*.{ts,tsx}'], rules: boundaries(['**/apps/**', '@epm2mod/site', '@epm2mod/local']) },
  { files: ['apps/site/**/*.{ts,tsx}'], rules: boundaries(['**/apps/local/**', '../../**', '@epm2mod/local']) },
  { files: ['apps/local/**/*.{ts,tsx}'], rules: boundaries(['**/apps/site/**', '../../**', '@epm2mod/site']) },
  {
    files: ['*.js'],
    extends: [js.configs.recommended],
    languageOptions: { globals: globals.node },
  },
)

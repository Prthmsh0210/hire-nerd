module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime', // If using new JSX transform
    'plugin:react-hooks/recommended',
    'prettier' // Add prettier last to override formatting rules
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh'],
  rules: {
    'react/prop-types': 'off', // Turn off prop-types if you use TypeScript or prefer not to use them
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
  },
}
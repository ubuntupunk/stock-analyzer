import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        // Browser globals
        window: "readonly",
        document: "readonly",
        console: "readonly",
        localStorage: "readonly",
        fetch: "readonly",
        navigator: "readonly",
        location: "readonly",
        history: "readonly",
        performance: "readonly",
        // Standard globals
        Promise: "readonly",
        Set: "readonly",
        Map: "readonly",
        Date: "readonly",
        Math: "readonly",
        JSON: "readonly",
        Array: "readonly",
        Object: "readonly",
        String: "readonly",
        Number: "readonly",
        Boolean: "readonly",
        Error: "readonly",
        RegExp: "readonly",
        parseInt: "readonly",
        parseFloat: "readonly",
        isNaN: "readonly",
        isFinite: "readonly",
        setTimeout: "readonly",
        setInterval: "readonly",
        clearTimeout: "readonly",
        clearInterval: "readonly",
        requestAnimationFrame: "readonly",
        cancelAnimationFrame: "readonly",
        // Custom globals
        Chart: "readonly",
        eventBus: "readonly",
        Validators: "readonly",
        Formatters: "readonly",
        module: "readonly",
        require: "readonly",
        process: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        exports: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { 
        args: "none",
        varsIgnorePattern: "^_",
        argsIgnorePattern: "^_"
      }],
      "no-console": ["off"],
      "no-undef": ["error"],
    },
  },
  {
    files: ["infrastructure/frontend/**/*.js"],
    rules: {
      "no-undef": ["error"],
      "no-unused-vars": ["warn", { 
        args: "none",
        varsIgnorePattern: "^_",
        argsIgnorePattern: "^_"
      }],
    },
  },
];

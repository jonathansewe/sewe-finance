# M1 exercise: `resolveTheme`

Rewrite `resolveTheme` yourself in `my_resolveTheme.ts`, without AI help.

```ts
resolveTheme(preference, systemScheme): 'dark' | 'light'
```

- `preference` is what the user picked: `'system'`, `'dark'` or `'light'`, but a corrupted saved value or `null` can also arrive.
- `systemScheme` is what the device reports: `'dark'`, `'light'`, or `null`/`undefined` when it reports nothing.
- An explicit `'dark'` or `'light'` always wins.
- Anything else follows the device; a device that reports nothing gets `'light'`.

Run your version (from `app/`):

```bash
npx jest --selectProjects exercises
```

Hint: two `if`s are enough. The reference is `app/theme/resolveTheme.ts`; don't open it until your tests pass.

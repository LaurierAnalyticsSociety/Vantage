# Environment-file encryption

Vantage uses [AGWA/git-crypt](https://github.com/AGWA/git-crypt) for opt-in encryption of `.env` and `.env.*` files. Example templates remain ordinary readable text. Local environment files remain ignored until deliberately selected for tracking.

## Initialize this working copy

`git-crypt` 0.8.0 is already installed on the initial development machine. New contributors can install it through their operating system package manager; on macOS, `brew install git-crypt`.

```sh
npm run secrets:init
```

The command initializes Git on `main` if needed, then initializes git-crypt. It is repeatable and preserves an existing unlocked key. If an encrypted repository is locked, unlock it rather than generating another key. Initialization does not stage files or create commits.

## Back up the encryption key

Choose a secure destination **outside this repository**, such as an encrypted personal vault:

```sh
npm run secrets:export -- /absolute/path/outside/Vantage/vantage.git-crypt-key
```

The command refuses existing destinations and paths inside the repository and writes owner-only permissions. Losing the repository's internal key without an external backup or GPG recipient can make encrypted contents inaccessible. Never commit the exported key.

## Track selected environment files

```sh
npm run secrets:track -- .env
npm run secrets:status
```

The tracking command checks the initialized required filter and attributes, stages only the selected files, and verifies the staged blob has git-crypt's encrypted header without printing its contents. Templates cannot be selected. It does not create a commit. Working-tree files remain readable to the authorized developer; Git stores encrypted contents.

The original specification's default rule against committing environment files still applies to plaintext files. Encrypted, explicitly selected environment files are the user-authorized exception. Keep generated logs, credentials caches, and exported keys ignored.

CI and production use injected environment variables with `APP_ENV=test` or `APP_ENV=production`; backend settings skip the local environment file in these modes, so no decryption key is needed to run isolated CI checks. Development uses the unlocked local `.env`.

## Collaborator access

Securely share the exported key outside Git. After cloning:

```sh
git-crypt unlock /secure/path/vantage.git-crypt-key
```

Alternatively, an owner can use `git-crypt add-gpg-user RECIPIENT` after choosing a verified GPG recipient. That command creates a commit containing encrypted key metadata; no GPG recipient or automatic commit is configured by this scaffold.

git-crypt protects selected file contents, not filenames or Git history metadata. Adding encryption does not remove plaintext from existing commits; initialization refuses an existing tracked environment file rather than silently treating its history as protected. The project has no existing Git history at initial setup.

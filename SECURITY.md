# Security policy

## Supported versions

Security fixes are issued for the latest release on the `main` branch. Older
builds are not patched; rebuild from `main` or update to the newest release.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Use GitHub's private reporting flow:

1. Open <https://github.com/WinterGate-IC/UmbraForge/security/advisories/new>.
2. Describe the issue, the affected version and, if possible, a minimal
   reproduction.

You will get an acknowledgement as soon as the report is reviewed. Please give
us a reasonable window to ship a fix before publishing details.

## Scope

In scope:

- the UmbraForge desktop application and its CLI;
- the Windows package and the offline Setup installer;
- the build and release scripts in `tools/`;
- the project file parser (`.umbra`) and the image/asset import paths.

Out of scope:

- issues that require a already-compromised machine or administrator rights;
- third-party libraries (report those upstream as well);
- optional `rembg`/`onnxruntime` installations;
- social-engineering or physical access.

## What this project already does

- **No secrets in the repository.** The build reads no tokens; releases are
  produced locally and uploaded over an authenticated channel.
- **No binaries or generated output are committed.** `.gitignore` excludes
  virtual environments, build trees, releases and caches.
- **Installer hardening.** Archive members are validated before extraction:
  absolute paths and `..` traversal are rejected, and Windows extended-length
  paths are used so a deep install folder cannot break or escape extraction.
- **Atomic project writes.** Saves are written to a temporary file and renamed
  into place, so an interrupted save cannot corrupt the previous project.
- **Checksums.** Release assets publish a SHA-256 digest; GitHub also reports
  the digest of every uploaded asset.
- **Dependency updates.** Dependabot watches Python and GitHub Actions
  dependencies; CodeQL and the test suite run on every push and pull request.
- **Licensing.** The build ships only the RSA *public* key used to verify a
  licence. The signing key is offline in a private repository, so no public
  build can mint a licence. See `OPEN_CORE.md`.

## Verifying a download

```powershell
Get-FileHash .\UmbraForge-<timestamp>.zip -Algorithm SHA256
```

Compare the result with the digest in the release notes. The same digest is
shown on the GitHub release asset.

## Licence and security model

UmbraForge is open source under the MIT licence. Publishing the source does not
weaken the application: there are no server-side secrets to expose, and every
release is reproducible from this repository with `tools/build_release.py`.
The trade-off is that anyone may fork and redistribute the code; that is
expected under MIT and is separate from vulnerability handling.

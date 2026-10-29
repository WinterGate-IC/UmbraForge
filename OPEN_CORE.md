# Open core

UmbraForge is published under the MIT licence. This document explains how a
paid edition can exist later **without** making the free edition worse and
without putting paid code in this repository.

## The free edition is complete

Every feature that exists in this repository works without a licence, a trial,
an account or a network call. There is no artificial limit, no disabled button
and no expiry. If you download UmbraForge today, that build is yours to use,
fork and change under MIT.

That will not change. MIT is irrevocable for the code that has already been
published.

## Where paid features live

Paid features are **new code** in a separate private repository. They are
packaged as an add-on and loaded at runtime:

```
umbraforge (this repository)  +  umbraforge_pro (private)  =  UmbraForge Pro
```

The public tree contains no paid implementation to copy. The private tree is
never pushed here, never vendored here and never added as a submodule.

The public app also ships the RSA **public** key in
[`licensing.py`](src/umbraforge/licensing.py) and therefore can *verify* a
licence. It cannot *create* one. The signing key stays offline.

## How an add-on is gated

1. At startup [`extensions.load()`](src/umbraforge/extensions.py) discovers
   add-ons through the `umbraforge.addons` entry point, the `umbraforge_pro`
   module name, or a bundled `umbraforge/addons/` folder.
2. An add-on declares the feature names it provides when it registers.
3. A feature is enabled only when a correctly signed licence covers that name.
   Menu entries for unlicensed features stay disabled; hooks for unlicensed
   features are skipped.
4. Every valuable operation in the add-on also calls
   `licensing.require("feature")` (or uses the `@licensing.licensed("feature")`
   decorator). Importing the code is not enough to run it.

Licence tokens are offline-verifiable RSA PKCS#1 v1.5 / SHA-256 signatures:

```
UF1.<base64url(payload)>.<base64url(signature)>
```

They can be bound to a machine id, carry an expiry date and list features.

```powershell
umbraforge --license                 # status as JSON
umbraforge --machine-id              # what a customer sends you
umbraforge --install-license <file>  # verify and store
```

## Building

The open-source build is the default and includes no add-ons:

```powershell
python tools/build_release.py
```

A private build passes the add-on package explicitly. It is the only way an
add-on can enter a frozen build:

```powershell
python tools/build_release.py --addon C:\path\to\umbraforge_pro
```

## What this does and does not protect

It is worth being honest, because it decides where the paid value should live.

**What it does**

- Keeps paid source out of the public repository and its history.
- Makes a copied add-on useless without a licence signed by the private key.
- Ties a licence to a person, a feature set, an expiry and optionally a machine.
- Makes casual sharing visible (a key bound to one machine will not work on
  another).
- Keeps the trade mark separate from the code: MIT lets someone fork the free
  app, but not call their fork UmbraForge.

**What it does not do**

- It is not DRM. A Python program can be decompiled, and a determined attacker
  can patch the check. Licensing raises the cost, it does not make extraction
  impossible.
- An offline licence cannot be revoked instantly. If you need revocation,
  validate online at startup with an offline grace period.
- MIT permits forks and resale of the **free** code. That is expected and is
  separate from the paid add-on.

**If a feature must be genuinely uncopyable**, put the valuable part on a server
and return only the result. That is the only approach that does not ship the
logic at all. The next best option is compiling the add-on to native code with
Nuitka or Cython so extraction is expensive.

## Checklist when adding a paid feature

- [ ] It is new code, not a flag that turns off an existing free feature.
- [ ] The public repository has no reference to its implementation.
- [ ] The handler calls `licensing.require("<feature>")` itself.
- [ ] Tests cover: no licence, wrong feature, expired licence, valid licence.
- [ ] The release notes do not imply the free edition is limited.

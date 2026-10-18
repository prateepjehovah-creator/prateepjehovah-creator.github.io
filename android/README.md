# நீலக்குரல் Android app

Trusted Web Activity for https://prateepjehovah-creator.github.io/. The app opens that site in Chrome without a URL bar once Digital Asset Links match the signing certificate.

Package id: `io.github.prateepjehovah_creator.neelam`

The upload keystore and its passwords are not in this repository. Copy `keystore.properties.example` to `keystore.properties` and point `storeFile` at the `.jks` file. PKCS12 uses the store password as the key password.

## Play App Signing

The fingerprint in `/.well-known/assetlinks.json` is the upload key. After the app is enrolled in Play App Signing, Play Console shows a second certificate under Setup → App signing → App signing key certificate. Add that SHA-256 fingerprint as another string in `sha256_cert_fingerprints` and deploy the site again. Until that second fingerprint is published, a Play-installed build can still show the browser URL bar.

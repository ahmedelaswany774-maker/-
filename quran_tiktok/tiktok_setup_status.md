# TikTok setup status

- Existing TikTok Developer app found in the connected account: `رواة الواقع`.
- App ID shown in the portal: `7673844607859394580`.
- App is in Draft under Production/Sandbox controls.
- Added products: Login Kit and Content Posting API.
- Scopes shown: `user.info.basic` and `video.upload`.
- Content Posting API currently has Upload to TikTok enabled by default; Direct Post is also shown as an option but has not been enabled.
- Login Kit is configured but requires a Redirect URI; the portal says Web configuration must be turned on to add redirect URIs.
- The portal indicates unsaved changes. Do not submit for review or save until redirect URI and app details are configured.
- App review requires app details, terms/privacy URLs, a review explanation, and a demo video; this is separate from the user's OAuth authorization.

- After adding Login Kit, the portal automatically showed `user.info.basic`.
- After adding Content Posting API, the portal automatically showed `video.upload`.
- The portal still shows unsaved changes and the Login Kit redirect URI section is not configured.

- Desktop platform was selected in Login Kit.
- Clicking Configure for Desktop navigated to the App Review area; the portal still displays unsaved changes. Redirect URI input was not exposed in the visible state, so no URI was entered or saved.
- App Review currently lists Login Kit, Content Posting API, `user.info.basic`, and `video.upload` as required review items.

- Clicking Save did not persist the configuration because TikTok reports 8 required-field errors: app icon, category, description, Terms of Service URL, Privacy Policy URL, at least one platform, app-review explanation, and a demo video.
- No review submission was made. The app remains in Draft and the configuration is unsaved.

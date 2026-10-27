# Zen Custom for macOS

A personal Zen UI fork with small browser windows and a system-wide New ChatGPT Message shortcut. Built and checked on macOS using Zen **1.23.4b** (Gecko 158.0.1). This is a local development build, not an official Zen release.

## Use

Open `~/Applications/Zen Custom.app`.

| Shortcut / control | Action |
| --- | --- |
| Option–Command–G | Open a fresh ChatGPT page in a small window |
| Option–Command–N | Open a small window with a search/address field |
| Command–L | Select the small window address field |
| Open in Space / Command–O | Move the live page into the selected Space |
| × / Command–W | Close the small window |
| File menu | New ChatGPT Message… and New Little Zen Window |

Global shortcuts work while Zen Custom is running, including when another app is active. Both shortcut registrations returned macOS status 0 in testing. If another app registers the same shortcut first, quit that app and relaunch Zen Custom; File menu commands remain available. Registration results are saved in the custom profile's `custom-commands/hotkey-status.json` (0 means success).

The profile is `~/Library/Application Support/Zen Custom/Profile`. It is separate from stock Zen and Arc; sign in to ChatGPT once in this profile. Opening the shortcut loads the ChatGPT home page and does not submit a message. Private windows remain private. This does not migrate existing browser accounts or cookies.

## Source and build

The local branch is `isaac/custom`. Upstream release source: `541ee55196395ee8082862b83c84c90ab41d9f6d`. The Little Zen backport is pinned to [wahyuabrory/little-zen](https://github.com/wahyuabrory/little-zen/tree/f1ed4b1109ae7ac8fac58b3dec6652a4bee556da), with custom changes described in `REVIEW.md`. Upstream Zen code retains its MPL-2.0 license and third-party notices.

From the repository root, with Python 3.10+ and Xcode Command Line Tools:

```sh
python3 custom/build-macos.py
```

The builder copies `/Applications/Zen.app`, validates and repacks its browser resources, compiles the Swift launcher/hotkey helper, and locally signs the resulting app. It reuses the release's precompiled Gecko engine; this is **not a full C++/Rust browser-engine rebuild**. The source loader and jar registration are also included for source builds. The base app and its profile are left intact. The previous custom app is retained as `~/Applications/Zen Custom.previous.app`.

**Updates require maintenance.** The stock updater is disabled inside this custom copy because it would overwrite the custom UI. Keep the stock Zen app updated; rebase the custom source to the matching release and run this builder and the smoke tests before replacing your custom build. Compatibility with later Zen versions is not assumed. The current build does not receive automatic security updates.

## Verification

The smoke test uses `marionette_driver==3.7.1` against a disposable profile, never your normal browsing profile. It checks actual page navigation, live tab transfer preserving an edited form and history state, ChatGPT shortcut routing, private context, the native command bridge, and custom JavaScript errors. macOS hotkey registration is checked separately. The ChatGPT login page was visually verified; account sign-in and submitting chats are intentionally left to you.

To run it, create a disposable profile with `marionette.port=2831`, `zen.custom.test-mode=true`, and `zen.welcome-screen.seen=true` in `user.js`, then launch:

```sh
"$HOME/Applications/Zen Custom.app/Contents/MacOS/zen-custom" --profile /tmp/zen-custom-test-profile --marionette --remote-allow-system-access -purgecaches about:blank
```

In a Python environment containing `marionette_driver==3.7.1`, run `python custom/tests/browser.py`. Do not enable Marionette or remote system access in your daily profile. Test mode disables automatic registration of global shortcuts so test instances do not compete with the installed app.

# Little Zen review — 2026-10-27

## Why the native feature is absent

[zen-browser/desktop#13450](https://github.com/zen-browser/desktop/pull/13450), titled “Start working on little zen,” was closed on 2026-06-14 and **never merged**. The author [said they closed it for cleanup and planned to return when they had more time](https://github.com/zen-browser/desktop/pull/13450#issuecomment-4703308129). That is evidence of deferred work, not a rejected finished feature or a production readiness endorsement. We cannot establish additional private reasons from this public thread.

The recorded review contains two automated unused-variable findings (width and height). Those findings are trivial to fix, but they are not an exhaustive review of the implementation. This fork uses its window size constants directly.

## Community implementations

- [12th-devs/little-zen#1](https://github.com/12th-devs/little-zen/pull/1) and [#2](https://github.com/12th-devs/little-zen/pull/2) were merged, not rejected.
- [#3](https://github.com/12th-devs/little-zen/pull/3) remained open. Its automated overview flagged that an existing toolbar threshold preference could retain a lower value; it listed no formal findings. This custom installation starts with a separate profile, and the backport raises the default threshold. Existing user overrides are respected.
- [#4](https://github.com/12th-devs/little-zen/pull/4) remained open. Its proposed changes include live-tab adoption, navigation/container behavior, download routing, theme sampling, and a new Space picker. There was no rejection explanation in the retrieved discussion. The whole unfinished branch was not adopted wholesale.
- [wahyuabrory/little-zen](https://github.com/wahyuabrory/little-zen/tree/f1ed4b1109ae7ac8fac58b3dec6652a4bee556da) provides a standalone backport suitable for the installed release. It was selected as the starting point and tested with the changes below.

The review directory contains the fetched public PR metadata, issue comments, review comments, and review states for these PRs. These files record what was public at review time, not a claim that no undisclosed issue exists.

## Changes made and checks

1. Initialize after DOMContentLoaded and observe delayed startup directly. Loading before the UI existed caused a null URL bar error in the first test build.
2. Add an editable search/address field, Command–L focus, accessible close button, and File menu commands. The backport's URL bar behavior explicitly disabled editing despite its README description.
3. Remove the blocking loading veil. A local HTML page finished loading but stayed invisible and could not accept keyboard input because the veil never cleared. Native loading/error UI and browser controls remain accessible.
4. Move the live tab into a Space through tab adoption. A test types unsaved form text, changes history state, clicks Open in Space, and verifies the same browsing context, form value, and history survive.
5. Keep private mode when opening/reusing little windows or selecting a destination main window. Private launch is covered in the browser test.
6. Match physical KeyN/KeyG codes; Option changes typed characters on macOS. The Option–Command–G browser event path is tested with the © character.
7. Add a native Carbon global-shortcut helper and a small allowlisted command queue. Both shortcuts registered successfully. A helper-generated command is verified end to end; no accessibility permission is required for Carbon registration.
8. Make debug URL logging opt-in and console-only, instead of always writing a browsing URL log to disk. Verify no debug log file is created.
9. Package into a separate app and profile with a local signature. Verify its bundle signature and run browser smoke tests against that bundle.

This is a personal UI fork on Zen 1.23.4b. These checks do not certify every inherited backport feature, extensions, authenticated ChatGPT workflows, or compatibility with future releases. The stock updater is disabled for this copy; see README.md for the maintenance implications.

/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/ */
const { setInterval } = ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");
const BASE = "chrome://browser/content/zen-custom/";

export const ZenCustom = {
  initialized: false,
  busy: false,
  queue: null,
  helper: null,

  async start() {
    if (this.initialized) return;
    this.initialized = true;
    const sheets = Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService);
    for (const filename of ["little-zen.css", "custom.css"]) {
      sheets.loadAndRegisterSheet(Services.io.newURI(BASE + filename), sheets.AGENT_SHEET);
    }
    this.queue = PathUtils.join(PathUtils.profileDir, "custom-commands");
    await IOUtils.makeDirectory(this.queue, { permissions: 0o700 });
    if (!Services.prefs.getBoolPref("zen.custom.test-mode", false)) {
      const binary = Services.dirsvc.get("GreBinD", Ci.nsIFile);
      binary.append("ZenCustomHotkeys");
      if (binary.exists()) {
        this.helper = Cc["@mozilla.org/process/util;1"].createInstance(Ci.nsIProcess);
        this.helper.init(binary);
        const args = ["--queue", this.queue, "--parent", String(Services.appinfo.processID)];
        this.helper.runwAsync(args, args.length, null, false);
      }
    }
    setInterval(() => this.drain(), 250);
  },

  async drain() {
    if (this.busy || !this.queue) return;
    this.busy = true;
    try {
      for (const path of await IOUtils.getChildren(this.queue)) {
        if (!/request-[a-z0-9-]+\.json$/i.test(PathUtils.filename(path))) continue;
        const stat = await IOUtils.stat(path);
        if (stat.size > 1024) { await IOUtils.remove(path); continue; }
        let request;
        try { request = await IOUtils.readJSON(path); } catch { await IOUtils.remove(path); continue; }
        if (!["little", "chatgpt"].includes(request.action)) { await IOUtils.remove(path); continue; }
        const win = this.mainWindow();
        if (!win) continue;
        await IOUtils.remove(path);
        this.open(request.action, win);
      }
    } catch (error) { console.error("Zen Custom command failed", error.name); }
    finally { this.busy = false; }
  },

  mainWindow() {
    const recent = Services.wm.getMostRecentWindow("navigator:browser");
    if (recent?.LittleZen && recent.gBrowserInit?.delayedStartupFinished) return recent;
    return [...Services.wm.getEnumerator("navigator:browser")].find(win => win.LittleZen && win.gBrowserInit?.delayedStartupFinished) || null;
  },

  open(action, win = this.mainWindow()) {
    if (!win?.LittleZen) return null;
    // Fixed destinations only. No remote code or arbitrary command payloads.
    return win.LittleZen.openLittleWindow(win, {
      url: action === "chatgpt" ? "https://chatgpt.com/" : null,
      expanded: true,
      source: "zen-custom-" + action,
    });
  },

  attach(win) {
    this.start().catch(error => console.error("Zen Custom startup failed", error));
    win.ZenCustom = this;
    const ready = () => {
      const doc = win.document;
      const popup = doc.getElementById("menu_FilePopup");
      if (popup && !doc.getElementById("zen-custom-new-chat")) {
        for (const [id, label, action, shortcut] of [
          ["zen-custom-new-little", "New Little Zen Window", "little", "⌥⌘N"],
          ["zen-custom-new-chat", "New ChatGPT Message…", "chatgpt", "⌥⌘G"],
        ]) {
          const item = doc.createXULElement("menuitem");
          item.id = id;
          item.setAttribute("label", label);
          item.setAttribute("acceltext", shortcut);
          item.addEventListener("command", () => this.open(action, win));
          popup.insertBefore(item, popup.firstChild);
        }
      }
      win.addEventListener("keydown", event => {
        if (event.code === "KeyG" && event.metaKey && event.altKey && !event.ctrlKey && !event.shiftKey && !event.repeat) {
          event.preventDefault(); event.stopImmediatePropagation();
          this.open("chatgpt", win);
        }
      }, true);
      const little = doc.documentElement.hasAttribute("zen-little-window") || win._zenStartupLittleWindow;
      if (little) this.addAddressBar(win);
    };
    if (win.gBrowserInit?.delayedStartupFinished) ready();
    else {
      const observer = subject => {
        if (subject !== win) return;
        Services.obs.removeObserver(observer, "browser-delayed-startup-finished");
        win.removeEventListener("unload", cleanup);
        ready();
      };
      const cleanup = () => Services.obs.removeObserver(observer, "browser-delayed-startup-finished");
      Services.obs.addObserver(observer, "browser-delayed-startup-finished");
      win.addEventListener("unload", cleanup, { once: true });
    }
  },

  addAddressBar(win) {
    const doc = win.document;
    if (doc.getElementById("zen-custom-address")) return;
    const box = doc.createXULElement("hbox");
    box.id = "zen-custom-address-box";
    box.setAttribute("flex", "1");
    const input = doc.createElementNS("http://www.w3.org/1999/xhtml", "input");
    input.id = "zen-custom-address";
    input.type = "text";
    input.placeholder = "Search or enter address";
    input.setAttribute("aria-label", "Search or enter address");
    input.setAttribute("autocomplete", "off");
    input.spellcheck = false;
    box.append(input);
    const toolbar = doc.getElementById("nav-bar-customization-target") || doc.getElementById("nav-bar");
    toolbar.insertBefore(box, doc.getElementById("urlbar-container"));
    const close = doc.createXULElement("toolbarbutton");
    close.id = "zen-custom-close";
    close.classList.add("toolbarbutton-1");
    close.setAttribute("label", "×");
    close.setAttribute("tooltiptext", "Close Little Zen window (⌘W)");
    close.setAttribute("aria-label", "Close Little Zen window");
    close.addEventListener("command", () => win.BrowserCommands.tryToCloseWindow());
    toolbar.append(close);
    const update = () => {
      if (doc.activeElement === input) return;
      const uri = win.gBrowser.selectedBrowser.currentURI.spec;
      input.value = /^(about:blank|about:newtab)$/.test(uri) ? "" : uri;
    };
    const listener = { onLocationChange: update, QueryInterface: ChromeUtils.generateQI(["nsIWebProgressListener", "nsISupportsWeakReference"]) };
    win.gBrowser.addProgressListener(listener);
    win.addEventListener("unload", () => { try { win.gBrowser.removeProgressListener(listener); } catch {} }, { once: true });
    input.addEventListener("keydown", async event => {
      if (event.key !== "Enter" || event.isComposing) return;
      event.preventDefault(); event.stopImmediatePropagation();
      const text = input.value.trim();
      if (!text) return;
      try {
        const flags = Ci.nsIURIFixup.FIXUP_FLAG_ALLOW_KEYWORD_LOOKUP;
        const info = Services.uriFixup.getFixupURIInfo(text, flags);
        const uri = info.preferredURI;
        // Never load privileged/browser script schemes from this web address field.
        if (!uri || !["http", "https", "file"].includes(uri.scheme)) return;
        input.blur();
        win.LittleZen.queueNavigation(win, uri.spec, { source: "custom-address" });
      } catch (error) { console.error("Zen Custom address could not be opened", error.name); }
    });
    win.addEventListener("keydown", event => {
      if (event.metaKey && !event.altKey && ["KeyL", "KeyK"].includes(event.code)) {
        event.preventDefault(); event.stopImmediatePropagation(); input.focus(); input.select();
      }
    }, true);
    update();
    if (!win.__littleZenPendingURL && !win.__littleZenRoutedURL) win.setTimeout(() => input.focus(), 250);
  },
};

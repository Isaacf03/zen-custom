"""Run against a disposable custom profile on Marionette port 2831."""
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.by import By
from marionette_driver.keys import Keys
import base64, json, subprocess, time

m = Marionette(port=2831)
m.start_session()
m.set_context('chrome')

def js(code):
    return m.execute_script(code)

def wait(code, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = js(code)
        if value: return value
        time.sleep(.15)
    raise AssertionError(code)

try:
    main = m.chrome_window_handles[0]
    m.switch_to_window(main)
    # Close only the test instance's earlier scratch windows.
    js('for(const w of [...Services.wm.getEnumerator("navigator:browser")]) { if(w !== window) w.close(); }')
    assert js('return !!window.ZenCustom && !!window.LittleZen')
    assert js('return !!document.getElementById("zen-custom-new-chat")')
    print('PASS: packaged features and File menu commands load', flush=True)

    js('window.ZenCustom.open("little")')
    wait('return [...Services.wm.getEnumerator("navigator:browser")].some(w=>w.document.getElementById("zen-custom-address"))')
    m.switch_to_window(m.chrome_window_handles[-1])
    assert js('return outerWidth <= 850 && outerHeight <= 650')
    fixture = Path('/tmp/zen-custom-test-page.html')
    fixture.write_text('<!doctype html><title>Zen Custom check</title><h1>Little Zen works</h1><input id="draft" value=""><a href="https://example.com/">Example</a>')
    field = m.find_element(By.ID, 'zen-custom-address')
    field.clear()
    field.send_keys(fixture.as_uri(), Keys.ENTER)
    wait('return gBrowser.selectedBrowser.currentURI.spec.startsWith("file:///tmp/zen-custom-test-page.html") || gBrowser.selectedBrowser.currentURI.spec.startsWith("file:///private/tmp/zen-custom-test-page.html")')
    wait('return !gBrowser.selectedBrowser.webProgress.isLoadingDocument && !document.documentElement.hasAttribute("zen-little-window-loading")')
    context_id = js('return gBrowser.selectedBrowser.browsingContext.id')
    m.set_context('content')
    m.find_element(By.ID, 'draft').send_keys('Keep this unsaved text')
    m.execute_script('history.pushState({check:123}, "", "#kept")')
    m.set_context('chrome')
    Path('/tmp/zen-custom-tested-window.png').write_bytes(base64.b64decode(m.screenshot()))
    js('window.dispatchEvent(new KeyboardEvent("keydown", {code:"KeyL",key:"l",metaKey:true,bubbles:true,cancelable:true}))')
    assert js('return document.activeElement.id') == 'zen-custom-address'
    assert js('return !!document.getElementById("zen-custom-close")')
    print('PASS: small window, editable address, Command-L, close control, page loads', flush=True)

    # Use the same Open in Space control the user will click.
    js('document.getElementById("zen-little-window-space-picker-open").dispatchEvent(new MouseEvent("mousedown", {button:0,bubbles:true}))')
    m.switch_to_window(main)
    wait('return [...Services.wm.getEnumerator("navigator:browser")].length === 1')
    assert js('return gBrowser.selectedBrowser.browsingContext.id') == context_id
    m.set_context('content')
    assert m.find_element(By.ID, 'draft').get_property('value') == 'Keep this unsaved text'
    assert m.execute_script('return history.state.check') == 123
    m.set_context('chrome')
    print('PASS: Open in Space preserves live page, form contents, and history', flush=True)

    # Option changes key text on macOS (e.g. G -> ©); physical KeyG must work.
    js('window.dispatchEvent(new KeyboardEvent("keydown", {code:"KeyG",key:"©",metaKey:true,altKey:true,bubbles:true,cancelable:true}))')
    wait('return [...Services.wm.getEnumerator("navigator:browser")].some(w=>w._zenStartupLittleWindow && w.gBrowser?.selectedBrowser.currentURI.spec.startsWith("https://chatgpt.com/"))')
    assert js('return [...Services.wm.getEnumerator("navigator:browser")].length') == 2
    print('PASS: Option-Command-G opens ChatGPT in a separate Little Zen window', flush=True)
    js('for(const w of [...Services.wm.getEnumerator("navigator:browser")]) if(w._zenStartupLittleWindow) w.close()')

    private = js('window.__customPrivate = OpenBrowserWindow({private:true}); return true')
    wait('return window.__customPrivate.gBrowserInit?.delayedStartupFinished && !!window.__customPrivate.LittleZen')
    js('window.__customPrivate.ZenCustom.open("little",window.__customPrivate)')
    wait('return [...Services.wm.getEnumerator("navigator:browser")].some(w=>w._zenStartupLittleWindow && w.gBrowserInit?.delayedStartupFinished)')
    assert js('const {PrivateBrowsingUtils:p}=ChromeUtils.importESModule("resource://gre/modules/PrivateBrowsingUtils.sys.mjs");return [...Services.wm.getEnumerator("navigator:browser")].filter(w=>w._zenStartupLittleWindow).every(w=>p.isWindowPrivate(w))')
    js('for(const w of [...Services.wm.getEnumerator("navigator:browser")]) if(w!==window) w.close()')
    print('PASS: private launch remains private', flush=True)

    queue = js('return ZenCustom.queue')
    subprocess.run([str(Path.home()/'Applications/Zen Custom.app/Contents/MacOS/ZenCustomHotkeys'), '--queue',queue,'--send','chatgpt'],check=True)
    wait('return [...Services.wm.getEnumerator("navigator:browser")].some(w=>w._zenStartupLittleWindow && w.gBrowser?.selectedBrowser.currentURI.spec.startsWith("https://chatgpt.com/"))')
    assert not (Path('/tmp/zen-custom-test-profile')/'little-zen-debug.log').exists()
    print('PASS: native shortcut bridge opens ChatGPT; no URL log file', flush=True)
    errors = js('return Services.console.getMessageArray().filter(x=>x.message?.includes("JavaScript Error") && /ZenCustom|LittleZen|zen-custom/.test(x.message)).map(x=>x.message)')
    assert not errors, errors
    print('PASS: no custom feature JavaScript errors', flush=True)
finally:
    m.delete_session()

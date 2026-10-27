from marionette_driver.marionette import Marionette
import json
m = Marionette(host='127.0.0.1', port=2831)
m.start_session()
m.set_context('chrome')
print(json.dumps(m.execute_script('''
const wins = [...Services.wm.getEnumerator("navigator:browser")];
return {
 windows: wins.map(w => ({ title: w.document.title, little: !!w.LittleZen, custom: !!w.ZenCustom,
   ready: w.gBrowserInit?.delayedStartupFinished, small: w.document.documentElement.hasAttribute("zen-little-window"),
   address: !!w.document.getElementById("zen-custom-address"), url: w.gBrowser?.selectedBrowser?.currentURI.spec,
   width: w.outerWidth, height: w.outerHeight })),
 binDir: Services.dirsvc.get("GreBinD", Ci.nsIFile).path,
 errors: Services.console.getMessageArray().filter(x => /LittleZen|Zen Custom|zen-custom|ZenCustom/.test(x.message || "")).map(x => x.message).slice(-12)
};
'''), indent=2))
m.delete_session()

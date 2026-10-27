import Foundation
import Darwin

let executable = URL(fileURLWithPath: CommandLine.arguments[0]).standardizedFileURL
let binDir = executable.deletingLastPathComponent()
let browser = binDir.appendingPathComponent("zen").path
var args = Array(CommandLine.arguments.dropFirst())
if !args.contains("-profile") && !args.contains("--profile") {
    let profile = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/Zen Custom/Profile")
    try FileManager.default.createDirectory(at: profile, withIntermediateDirectories: true,
        attributes: [.posixPermissions: 0o700])
    let prefs = profile.appendingPathComponent("user.js")
    if !FileManager.default.fileExists(atPath: prefs.path) {
        try """
        user_pref("zen.welcome-screen.seen", true);
        user_pref("browser.shell.checkDefaultBrowser", false);
        user_pref("browser.startup.homepage", "about:blank");
        user_pref("extensions.littleZen.debugRouting", false);
        """.write(to: prefs, atomically: true, encoding: .utf8)
    }
    args = ["-profile", profile.path] + args
}
setenv("MOZ_APP_REMOTINGNAME", "zen-custom", 1)
let strings = ([browser, "-no-remote"] + args).map { strdup($0) }
var pointers = strings + [nil]
execv(browser, &pointers)
perror("Could not launch Zen Custom")
exit(1)

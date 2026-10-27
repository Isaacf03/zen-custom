import AppKit
import Carbon
import Foundation
import Darwin

let arguments = CommandLine.arguments
func option(_ name: String) -> String? {
    guard let index = arguments.firstIndex(of: name), index + 1 < arguments.count else { return nil }
    return arguments[index + 1]
}
guard let queuePath = option("--queue") else { exit(2) }
let queue = URL(fileURLWithPath: queuePath, isDirectory: true)
try FileManager.default.createDirectory(at: queue, withIntermediateDirectories: true,
    attributes: [.posixPermissions: 0o700])

func enqueue(_ action: String) {
    guard ["little", "chatgpt"].contains(action) else { return }
    let file = queue.appendingPathComponent("request-\(UUID().uuidString).json")
    do {
        let data = try JSONSerialization.data(withJSONObject: ["action": action])
        try data.write(to: file, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
    } catch { fputs("Zen Custom could not queue a shortcut.\n", stderr) }
}

if let action = option("--send") { enqueue(action); exit(0) }
guard let parentString = option("--parent"), let parentPID = Int32(parentString) else { exit(2) }
let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
var eventType = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
func activateParent() {
    if let value = option("--parent"), let pid = Int32(value) {
        NSRunningApplication(processIdentifier: pid)?.activate(options: [])
    }
}
let callback: EventHandlerUPP = { _, event, _ in
    var key = EventHotKeyID()
    let result = GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID),
        nil, MemoryLayout<EventHotKeyID>.size, nil, &key)
    guard result == noErr else { return result }
    if key.id == 1 { enqueue("little") }
    if key.id == 2 { enqueue("chatgpt") }
    activateParent()
    return noErr
}
var handler: EventHandlerRef?
let handlerStatus = InstallEventHandler(GetApplicationEventTarget(), callback, 1, &eventType, nil, &handler)
var refs: [EventHotKeyRef] = []
var status: [String: Int32] = ["handler": handlerStatus]
for (id, keyCode, name) in [(UInt32(1), UInt32(kVK_ANSI_N), "little"), (UInt32(2), UInt32(kVK_ANSI_G), "chatgpt")] {
    var ref: EventHotKeyRef?
    let code = RegisterEventHotKey(keyCode, UInt32(cmdKey | optionKey), EventHotKeyID(signature: 0x5A435553, id: id),
        GetApplicationEventTarget(), 0, &ref)
    status[name] = code
    if let ref { refs.append(ref) }
}
if let data = try? JSONSerialization.data(withJSONObject: status) {
    try? data.write(to: queue.appendingPathComponent("hotkey-status.json"), options: .atomic)
}
let parentWatch = DispatchSource.makeProcessSource(identifier: parentPID, eventMask: .exit, queue: .main)
parentWatch.setEventHandler { app.terminate(nil) }
parentWatch.resume()
if kill(parentPID, 0) != 0 { exit(0) }
app.run()
for ref in refs { UnregisterEventHotKey(ref) }
if let handler { RemoveEventHandler(handler) }

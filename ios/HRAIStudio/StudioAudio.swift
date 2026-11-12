import AVFoundation
import Foundation
import Combine

@MainActor final class StudioAudio: ObservableObject {
    @Published private(set) var monitoring = false
    @Published private(set) var recording = false
    @Published private(set) var latencyMS: Double = 0
    @Published private(set) var status = "Ready"
    private let engine = AVAudioEngine()
    private let vocal = AVAudioMixerNode()
    private let vocalTrim = AVAudioUnitEQ(numberOfBands: 0)
    private var vocalLevel: Float = 0.8
    private let beat = AVAudioPlayerNode()
    private var configured = false
    private var writer: AVAudioFile?
    private var beatFile: AVAudioFile?
    private var tapInstalled = false

    func prepare() async throws {
        guard !configured else { return }
        guard await AVAudioApplication.requestRecordPermission() else {
            throw NSError(domain: "HRAI", code: 1, userInfo: [NSLocalizedDescriptionKey: "Microphone permission denied"])
        }
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [])
        try session.setPreferredSampleRate(48000)
        try session.setPreferredIOBufferDuration(0.002667)
        try session.setActive(true)
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.channelCount > 0, format.sampleRate > 0 else {
            throw NSError(domain: "HRAI", code: 2, userInfo: [NSLocalizedDescriptionKey: "No audio input"])
        }
        engine.attach(vocal)
        engine.attach(vocalTrim)
        engine.attach(beat)
        engine.connect(input, to: vocalTrim, format: format)
        engine.connect(vocalTrim, to: vocal, format: format)
        engine.connect(vocal, to: engine.mainMixerNode, format: nil)
        engine.connect(beat, to: engine.mainMixerNode, format: nil)
        vocal.outputVolume = 0
        beat.volume = 0.35
        engine.mainMixerNode.outputVolume = 0.7
        engine.prepare()
        try engine.start()
        configured = true
        latencyMS = (session.inputLatency + session.outputLatency + 2 * session.ioBufferDuration) * 1000
        status = session.currentRoute.outputs.map { $0.portName }.joined(separator: ", ")
    }

    func monitor(_ enabled: Bool) {
        let outputs = AVAudioSession.sharedInstance().currentRoute.outputs
        guard !enabled || (!outputs.isEmpty && outputs.allSatisfy({ $0.portType != .builtInSpeaker && $0.portType != .builtInReceiver })) else {
            status = "Connect headphones before monitoring"; return
        }
        vocal.outputVolume = enabled ? vocalLevel : 0
        monitoring = enabled
    }

    func setVocal(_ value: Float) { vocalLevel = min(1, max(0, value)); if monitoring { vocal.outputVolume = vocalLevel } }
    func setTrim(_ db: Float) { vocalTrim.globalGain = min(18, max(0, db)) }
    func setBeat(_ value: Float) { beat.volume = min(1, max(0, value)) }
    func setMaster(_ value: Float) { engine.mainMixerNode.outputVolume = min(1, max(0, value)) }

    func loadBeat(_ url: URL) throws {
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        let local = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString).appendingPathExtension(url.pathExtension)
        try FileManager.default.copyItem(at: url, to: local)
        beatFile = try AVAudioFile(forReading: local)
    }

    func record(to url: URL) throws {
        guard configured, !recording else { return }
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        let file = try AVAudioFile(forWriting: url, settings: format.settings, commonFormat: format.commonFormat, interleaved: format.isInterleaved)
        writer = file
        input.installTap(onBus: 0, bufferSize: 256, format: format) { buffer, _ in
            do { try file.write(from: buffer) } catch { NSLog("HRAI recording write failed: %@", error.localizedDescription) }
        }
        tapInstalled = true
        recording = true
        if let file = beatFile { beat.stop(); beat.scheduleFile(file, at: nil); beat.play() }
    }

    func stop() {
        beat.stop()
        if tapInstalled { engine.inputNode.removeTap(onBus: 0); tapInstalled = false }
        writer = nil
        recording = false
    }
}

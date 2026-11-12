import SwiftUI
import UniformTypeIdentifiers

@main struct HRAIStudioApp: App {
    var body: some Scene { WindowGroup { StudioView() } }
}

struct StudioView: View {
    @StateObject private var audio = StudioAudio()
    @State private var vocal = 0.8
    @State private var trim = 0.0
    @State private var beat = 0.35
    @State private var master = 0.7
    @State private var importing = false
    @State private var error = ""
    @State private var take: URL?
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text("HRAI!").font(.system(size: 48, weight: .black))
                    Text("STUDIO / NATIVE AUDIO").font(.caption.monospaced())
                    Text(audio.status)
                    Text("Estimated I/O: \(audio.latencyMS, specifier: "%.1f") ms").font(.caption.monospaced())
                    Button(audio.monitoring ? "MONITOR ON" : "MONITOR OFF") {
                        Task { do { try await audio.prepare(); audio.monitor(!audio.monitoring); audio.setVocal(Float(vocal)) } catch { self.error = error.localizedDescription } }
                    }.buttonStyle(.borderedProminent)
                    Text("VOCAL CUE"); Slider(value: $vocal).onChange(of: vocal) { _, v in audio.setVocal(Float(v)) }
                    Text("INPUT MONITOR TRIM +\(trim, specifier: "%.0f") dB"); Slider(value: $trim, in: 0...18).onChange(of: trim) { _, v in audio.setTrim(Float(v)) }
                    Text("BEAT CUE"); Slider(value: $beat).onChange(of: beat) { _, v in audio.setBeat(Float(v)) }
                    Text("MASTER"); Slider(value: $master).onChange(of: master) { _, v in audio.setMaster(Float(v)) }
                    Button("IMPORT BEAT") { importing = true }.disabled(audio.recording)
                    Button(audio.recording ? "STOP" : "RECORD") {
                        if audio.recording { audio.stop(); return }
                        Task {
                            do {
                                try await audio.prepare()
                                let folder = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
                                let url = folder.appendingPathComponent("Take-\(UUID().uuidString).caf")
                                try audio.record(to: url); take = url
                            } catch { self.error = error.localizedDescription }
                        }
                    }.buttonStyle(.borderedProminent).tint(.red)
                    if let take, !audio.recording {
                        HStack {
                            Button("PLAY MIX") { do { try audio.review() } catch { self.error = error.localizedDescription } }
                            Button("SOLO VOCAL") { do { try audio.review(vocalOnly: true) } catch { self.error = error.localizedDescription } }
                            Button("STOP") { audio.stopPlayback() }
                        }.buttonStyle(.bordered)
                        ShareLink(item: take) { Text("EXPORT TAKE") }
                    }
                    if !error.isEmpty { Text(error).foregroundStyle(.red) }
                }.padding(24)
            }.preferredColorScheme(.dark)
            .fileImporter(isPresented: $importing, allowedContentTypes: [.audio]) { result in
                do { try audio.loadBeat(result.get()) } catch { self.error = error.localizedDescription }
            }
        }
    }
}

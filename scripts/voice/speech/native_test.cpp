// Native CDR round trip only: no ROS initialization, endpoints or playback.
#include "tts_abi.hpp"
#include "catalog.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>

static std::string quoted(const std::string& input) {
    std::string output = "\"";
    for (const unsigned char byte : input) {
        if (byte == '"' || byte == '\\') {
            output += '\\'; output += static_cast<char>(byte);
        } else if (byte < 0x20) {
            char escaped[7];
            std::snprintf(escaped, sizeof(escaped), "\\u%04x", static_cast<unsigned>(byte));
            output += escaped;
        } else output += static_cast<char>(byte);
    }
    return output+'"';
}

// nlohmann's native to_json output is a sorted map. Specify every Tts field and
// a nonzero UUID so equality detects unintended metadata or identity changes.
static std::string request(const std::string& text, int type=1,
                           const std::string& file="/native/original.wav",
                           const std::string& language="zh") {
    return "{\"goal\":{\"file_path\":"+quoted(file)+
        ",\"format\":\"wav\",\"is_break\":true,\"language\":"+quoted(language)+
        ",\"need_save\":true,\"pitch\":13,\"speaker\":\"speaker-sentinel\","
        "\"speed\":42,\"text\":"+quoted(text)+",\"type\":"+std::to_string(type)+
        ",\"volume\":77},\"goal_id\":{\"uuid\":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]}}";
}

struct CdrView {
    const unsigned char* data;
    uint32_t length;
};

static CdrView cdr_view(const void* payload, uint32_t capacity) {
    // Verified native SerializedPayload_t ABI: length+4, data+8, max_size+16.
    // Read these scalar values without declaring or owning the vendor class.
    static_assert(sizeof(void*) == 8);
    assert(payload);
    const auto fields = static_cast<const unsigned char*>(payload);
    CdrView view {};
    uint32_t maximum = 0;
    std::memcpy(&view.length, fields+4, sizeof(view.length));
    std::memcpy(&view.data, fields+8, sizeof(view.data));
    std::memcpy(&maximum, fields+16, sizeof(maximum));
    assert(view.data && view.length > 4 && view.length <= maximum && maximum == capacity);
    return view;
}

static std::string compact_json(const std::string& input) {
    // The native helper pretty-prints. Remove whitespace only outside strings;
    // Chinese punctuation, spaces inside warnings and escapes stay unchanged.
    std::string output;
    bool string = false, escaped = false;
    for (const char byte : input) {
        if (!string && (byte == ' ' || byte == '\n' || byte == '\r' || byte == '\t')) continue;
        output += byte;
        if (escaped) { escaped = false; continue; }
        if (string && byte == '\\') { escaped = true; continue; }
        if (byte == '"') string = !string;
    }
    assert(!string && !escaped);
    return output;
}

static std::string round_trip(const std::string& input) {
    const auto unchanged = input;
    void* bytes = nullptr;
    uint32_t size = 0;
    serialize_sys_task_msgs_action_Tts_SendGoal_Request_json_to_cdr(input.c_str(), &bytes, &size);
    const auto view = cdr_view(bytes, size);
    const std::vector<unsigned char> before(view.data, view.data+view.length);
    char* output = nullptr;
    size_t output_size = 0;
    try {
        deserialize_sys_task_msgs_action_Tts_SendGoal_Request_cdr_to_json(view.data, view.length, &output, &output_size);
        assert(output && output_size > 0);
        assert(input == unchanged && std::memcmp(view.data, before.data(), view.length) == 0);
        const std::string result(output);
        // Some generated APIs include the terminator in their reported size.
        assert(output_size == result.size() || output_size == result.size()+1);
        free_sys_task_msgs_action_Tts_SendGoal_Request_json_str(output);
        delete_sys_task_msgs_action_Tts_SendGoal_Request_serialize_data(bytes);
        return compact_json(result);
    } catch (...) {
        if (output) free_sys_task_msgs_action_Tts_SendGoal_Request_json_str(output);
        delete_sys_task_msgs_action_Tts_SendGoal_Request_serialize_data(bytes);
        throw;
    }
}

static void malformed_cdr_stays_rejected() {
    void* bytes = nullptr;
    uint32_t size = 0;
    serialize_sys_task_msgs_action_Tts_SendGoal_Request_json_to_cdr(request("未知测试").c_str(), &bytes, &size);
    const auto view = cdr_view(bytes, size);
    std::vector<unsigned char> malformed(view.data, view.data+view.length);
    malformed[0] = 0xff;
    malformed[1] = 0xff; // Unsupported CDR encapsulation, rejected by the native API.
    char* output = nullptr;
    size_t output_size = 0;
    bool rejected = false;
    try {
        deserialize_sys_task_msgs_action_Tts_SendGoal_Request_cdr_to_json(
            malformed.data(), static_cast<uint32_t>(malformed.size()), &output, &output_size);
    } catch (...) { rejected = true; }
    if (output) free_sys_task_msgs_action_Tts_SendGoal_Request_json_str(output);
    delete_sys_task_msgs_action_Tts_SendGoal_Request_serialize_data(bytes);
    assert(rejected);
}

int main(int argc, char** argv) {
    if (argc != 2 || (std::string(argv[1]) != "--expect-files" &&
                      std::string(argv[1]) != "--expect-fallback" &&
                      std::string(argv[1]) != "--expect-native")) {
        std::fputs("usage: voice_speech_native_test --expect-files|--expect-fallback|--expect-native\n", stderr);
        return 2;
    }
    assert(!speech_catalog.empty());
    const std::string mode(argv[1]);
    size_t tested = 0;
    for (const auto& row : speech_catalog) {
        const std::string path = std::string(SPEECH_AUDIO_ROOT)+"/"+row.second.first+".wav";
        const bool readable = access(path.c_str(), R_OK) == 0;
        if (mode == "--expect-files") assert(readable);
        if (mode == "--expect-fallback") assert(!readable);
        const auto input = request(row.first);
        const auto expected = mode == "--expect-native" ? input : readable ?
            request(row.first, 0, path) : request(row.second.second, 1, "/native/original.wav", "en");
        const auto actual = round_trip(input);
        if (actual != expected) {
            std::fprintf(stderr, "ROUNDTRIP_MISMATCH id=%s\nEXPECTED=%s\nACTUAL=%s\n",
                         row.second.first.c_str(), expected.c_str(), actual.c_str());
            return 1;
        }
        // Already localized FILE goals and near-matches must be byte-for-byte
        // equivalent in their full canonical request, not merely retain text.
        const auto file = request(row.first, 0);
        assert(round_trip(file) == file);
        const auto extra = request(row.first+" [not an exact catalog entry]");
        assert(round_trip(extra) == extra);
        ++tested;
    }
    for (const auto& text : {"未收录的新语音", "English unchanged.", ""}) {
        const auto unknown = request(text);
        assert(round_trip(unknown) == unknown);
    }
    malformed_cdr_stays_rejected();
    std::printf("NATIVE_REQUEST_CDR_ROUNDTRIP_PASS; ENTRIES=%zu; MODE=%s; UUID_METADATA_INPUT_PRESERVED=1; GOALS_SENT=0; PLAYBACK=0\n",
                tested, mode.c_str());
}

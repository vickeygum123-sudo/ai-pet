#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_arduino_version.h>
#include <HTTPClient.h>
#if ESP_ARDUINO_VERSION_MAJOR >= 3
#include <ESP_I2S.h>
#define AI_PET_USE_ESP_I2S 1
#else
#include <I2S.h>
#define AI_PET_USE_ESP_I2S 0
#endif
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

#include "BringupConfig.h"

namespace {

constexpr const char *kPrefsNamespace = "ai-pet-fw";
constexpr const char *kPrefsKeySsid = "wifi_ssid";
constexpr const char *kPrefsKeyPassword = "wifi_pass";
constexpr const char *kPrefsKeyCloudBaseUrl = "cloud_url";
constexpr const char *kPrefsKeySessionId = "session_id";
constexpr const char *kPrefsKeyDeviceId = "device_id";
constexpr const char *kPrefsKeyLocale = "locale";

constexpr uint32_t kSerialBaud = AI_PET_SERIAL_BAUD;
constexpr uint32_t kAudioSampleRateHz = AI_PET_AUDIO_SAMPLE_RATE_HZ;
constexpr uint32_t kAudioCaptureMs = AI_PET_AUDIO_CAPTURE_MS;
constexpr uint32_t kAudioCaptureStallTimeoutMs = AI_PET_AUDIO_CAPTURE_STALL_TIMEOUT_MS;
constexpr bool kEnablePlayback = AI_PET_ENABLE_PLAYBACK != 0;
constexpr bool kEnableLightweightVad = AI_PET_ENABLE_LIGHTWEIGHT_VAD != 0;
constexpr uint32_t kVadFrameMs = AI_PET_VAD_FRAME_MS;
constexpr uint32_t kVadBootstrapMs = AI_PET_VAD_BOOTSTRAP_MS;
constexpr uint32_t kVadPreRollMs = AI_PET_VAD_PREROLL_MS;
constexpr uint32_t kVadMinCaptureMs = AI_PET_VAD_MIN_CAPTURE_MS;
constexpr uint32_t kVadMaxCaptureMs = AI_PET_VAD_MAX_CAPTURE_MS;
constexpr uint32_t kVadEndSilenceMs = AI_PET_VAD_END_SILENCE_MS;
constexpr uint32_t kVadEndConfirmMs = AI_PET_VAD_END_CONFIRM_MS;
constexpr uint32_t kVadStartTriggerFrames = AI_PET_VAD_START_TRIGGER_FRAMES;
constexpr uint32_t kVadStartRatioNum = AI_PET_VAD_START_RATIO_NUM;
constexpr uint32_t kVadStartRatioDen = AI_PET_VAD_START_RATIO_DEN;
constexpr uint32_t kVadStartOffsetAbs = AI_PET_VAD_START_OFFSET_ABS;
constexpr uint32_t kVadStartFloorAbs = AI_PET_VAD_START_FLOOR_ABS;
constexpr uint32_t kVadEndRatioNum = AI_PET_VAD_END_RATIO_NUM;
constexpr uint32_t kVadEndRatioDen = AI_PET_VAD_END_RATIO_DEN;
constexpr uint32_t kVadEndOffsetAbs = AI_PET_VAD_END_OFFSET_ABS;
constexpr uint32_t kVadEndFloorAbs = AI_PET_VAD_END_FLOOR_ABS;
constexpr uint32_t kVadResumeTriggerFrames = AI_PET_VAD_RESUME_TRIGGER_FRAMES;
constexpr uint32_t kVadResumeOffsetAbs = AI_PET_VAD_RESUME_OFFSET_ABS;
constexpr uint32_t kVadNearMaxEndSilenceMs = AI_PET_VAD_NEAR_MAX_END_SILENCE_MS;
constexpr uint32_t kVadNearMaxWindowMs = AI_PET_VAD_NEAR_MAX_WINDOW_MS;
constexpr uint32_t kVadPostSpeechMaxMs = AI_PET_VAD_POST_SPEECH_MAX_MS;
constexpr uint32_t kVadPostSpeechGuardMinSilenceMs =
    AI_PET_VAD_POST_SPEECH_GUARD_MIN_SILENCE_MS;
constexpr size_t kVadFrameSampleCount = (kAudioSampleRateHz * kVadFrameMs) / 1000;
constexpr size_t kVadBootstrapFrameCount =
    (kVadBootstrapMs / kVadFrameMs) > 0 ? (kVadBootstrapMs / kVadFrameMs) : 1;
constexpr size_t kVadPreRollSampleCount = (kAudioSampleRateHz * kVadPreRollMs) / 1000;
constexpr size_t kVadMaxSampleCount = (kAudioSampleRateHz * kVadMaxCaptureMs) / 1000;
constexpr uint32_t kWifiConnectTimeoutMs = AI_PET_WIFI_CONNECT_TIMEOUT_MS;
constexpr uint32_t kWifiRetryIntervalMs = AI_PET_WIFI_RETRY_INTERVAL_MS;
constexpr uint32_t kCloudConnectTimeoutMs = AI_PET_CLOUD_CONNECT_TIMEOUT_MS;
constexpr uint32_t kHttpTimeoutMs = AI_PET_HTTP_TIMEOUT_MS;
constexpr int kPdmDataPin = AI_PET_PDM_DATA_PIN;
constexpr int kPdmClockPin = AI_PET_PDM_CLOCK_PIN;
constexpr uint32_t kPlaybackDefaultSampleRateHz = AI_PET_PLAYBACK_DEFAULT_SAMPLE_RATE_HZ;
constexpr uint8_t kPlaybackBitsPerSample = AI_PET_PLAYBACK_BITS_PER_SAMPLE;
constexpr uint8_t kPlaybackChannels = AI_PET_PLAYBACK_CHANNELS;
constexpr int kPlaybackBclkPin = AI_PET_MAX98357_BCLK_PIN;
constexpr int kPlaybackLrclkPin = AI_PET_MAX98357_LRCLK_PIN;
constexpr int kPlaybackDinPin = AI_PET_MAX98357_DIN_PIN;
constexpr size_t kPlaybackWriteChunkBytes = AI_PET_PLAYBACK_I2S_WRITE_CHUNK_BYTES;
constexpr size_t kI2sReadChunkBytes = AI_PET_I2S_READ_CHUNK_BYTES;

const char *kFirmwareVersion = AI_PET_FIRMWARE_VERSION;
const char *kDefaultDeviceId = AI_PET_DEFAULT_DEVICE_ID;
const char *kDefaultLocale = AI_PET_DEFAULT_LOCALE;
const char *kDefaultCloudBaseUrl = AI_PET_DEFAULT_CLOUD_BASE_URL;
const char *kPairingApPassword = AI_PET_PAIRING_AP_PASSWORD;
const char *kCloudCaCertPem = nullptr;
constexpr bool kAllowInsecureHttps = AI_PET_ALLOW_INSECURE_HTTPS != 0;

enum class DeviceState {
  Booting,
  PairingReady,
  ConnectingWiFi,
  WiFiConnected,
  ConnectingCloud,
  ReadyToSpeak,
  Listening,
  Thinking,
  Speaking,
  Error,
};

enum class ErrorCode {
  None,
  ConfigMissing,
  WiFiConnectFailed,
  CloudProbeFailed,
  TlsConfigRequired,
  MicInitFailed,
  MicCaptureFailed,
  CloudRequestFailed,
  JsonParseFailed,
  CloudAudioMissing,
  PlaybackInitFailed,
  PlaybackDecodeFailed,
  PlaybackUnsupported,
  PlaybackWriteFailed,
};

enum class CaptureStrategy {
  FixedWindow,
  LightweightVad,
};

enum class VadState {
  Priming,
  WaitingForSpeech,
  Speaking,
  TrailingSilence,
  ConfirmingEnd,
  FallbackFixedWindow,
  Complete,
};

enum class CaptureExitReason {
  FixedWindow,
  EndOfSpeech,
  FallbackNoSpeech,
  MaxCapture,
};

struct RuntimeConfig {
  String ssid;
  String password;
  String cloudBaseUrl;
  String sessionId;
  String deviceId;
  String locale;

  bool hasWiFiCredentials() const { return !ssid.isEmpty(); }

  bool hasCloudConfig() const {
    return !cloudBaseUrl.isEmpty() && !sessionId.isEmpty() && !deviceId.isEmpty();
  }
};

struct ParsedUrl {
  bool valid = false;
  bool secure = false;
  String host;
  uint16_t port = 0;
  String basePath = "";
};

struct CapturedAudio {
  int16_t *samples = nullptr;
  size_t byteCount = 0;
  size_t sampleCount = 0;
  uint32_t durationMs = 0;
  CaptureStrategy strategy = CaptureStrategy::FixedWindow;
  CaptureExitReason exitReason = CaptureExitReason::FixedWindow;
  bool speechDetected = false;
};

struct CloudResponseSummary {
  int httpStatus = 0;
  String sessionState;
  String transcript;
  String responseText;
  String audioBase64;
  String audioFormat;
  String audioUrl;
  String fallbackMode;
  String runtimeFailureCode;
};

struct ParsedWavePcm {
  uint16_t audioFormat = 0;
  uint16_t channelCount = 0;
  uint32_t sampleRateHz = 0;
  uint16_t bitsPerSample = 0;
  const uint8_t *pcmData = nullptr;
  size_t pcmByteCount = 0;
};

struct HttpResponseMetadata {
  int statusCode = 0;
  bool chunked = false;
  int contentLength = -1;
  String contentType;
};

Preferences g_preferences;
WebServer g_server(80);
RuntimeConfig g_config;
DeviceState g_state = DeviceState::Booting;
ErrorCode g_lastError = ErrorCode::None;
String g_lastErrorDetail;
String g_lastTranscript;
String g_lastResponseText;
String g_lastRuntimeFailureCode = "none";
String g_lastSessionState = "unknown";
String g_lastPlaybackResult = "idle";
String g_lastPlaybackAudioFormat = "none";
uint32_t g_lastPlaybackSampleRateHz = 0;
uint16_t g_lastPlaybackChannels = 0;
size_t g_lastPlaybackPcmBytes = 0;
String g_pairingApSsid;
bool g_pairingPortalActive = false;
bool g_micInitialized = false;
bool g_playbackInitialized = false;
bool g_wifiConnected = false;
bool g_cloudReachable = false;
bool g_reconnectRequested = false;
uint32_t g_lastReconnectAttemptAtMs = 0;
uint32_t g_turnCounter = 0;
#if AI_PET_USE_ESP_I2S
I2SClass g_i2s;
I2SClass g_playbackI2s;
#endif

String trimCopy(const String &value) {
  String copy = value;
  copy.trim();
  return copy;
}

String chipSuffix() {
  const uint64_t mac = ESP.getEfuseMac();
  char buffer[7];
  snprintf(buffer, sizeof(buffer), "%06llX", mac & 0xFFFFFFULL);
  return String(buffer);
}

String defaultDeviceId() {
  return String(kDefaultDeviceId) + "-" + chipSuffix();
}

const char *deviceStateToString(const DeviceState state) {
  switch (state) {
  case DeviceState::Booting:
    return "booting";
  case DeviceState::PairingReady:
    return "pairing_ready";
  case DeviceState::ConnectingWiFi:
    return "connecting_wifi";
  case DeviceState::WiFiConnected:
    return "wifi_connected";
  case DeviceState::ConnectingCloud:
    return "connecting_cloud";
  case DeviceState::ReadyToSpeak:
    return "ready_to_speak";
  case DeviceState::Listening:
    return "listening";
  case DeviceState::Thinking:
    return "thinking";
  case DeviceState::Speaking:
    return "speaking";
  case DeviceState::Error:
    return "error";
  }
  return "unknown";
}

const char *errorCodeToString(const ErrorCode code) {
  switch (code) {
  case ErrorCode::None:
    return "none";
  case ErrorCode::ConfigMissing:
    return "config_missing";
  case ErrorCode::WiFiConnectFailed:
    return "wifi_connect_failed";
  case ErrorCode::CloudProbeFailed:
    return "cloud_connect_failed";
  case ErrorCode::TlsConfigRequired:
    return "tls_config_required";
  case ErrorCode::MicInitFailed:
    return "mic_init_failed";
  case ErrorCode::MicCaptureFailed:
    return "audio_capture_failed";
  case ErrorCode::CloudRequestFailed:
    return "cloud_request_failed";
  case ErrorCode::JsonParseFailed:
    return "json_parse_failed";
  case ErrorCode::CloudAudioMissing:
    return "cloud_audio_missing";
  case ErrorCode::PlaybackInitFailed:
    return "playback_init_failed";
  case ErrorCode::PlaybackDecodeFailed:
    return "playback_decode_failed";
  case ErrorCode::PlaybackUnsupported:
    return "playback_unsupported";
  case ErrorCode::PlaybackWriteFailed:
    return "playback_write_failed";
  }
  return "unknown";
}

const char *captureStrategyToString(const CaptureStrategy strategy) {
  switch (strategy) {
  case CaptureStrategy::FixedWindow:
    return "fixed_window";
  case CaptureStrategy::LightweightVad:
    return "lightweight_vad";
  }
  return "unknown";
}

const char *vadStateToString(const VadState state) {
  switch (state) {
  case VadState::Priming:
    return "priming";
  case VadState::WaitingForSpeech:
    return "waiting_for_speech";
  case VadState::Speaking:
    return "speaking";
  case VadState::TrailingSilence:
    return "trailing_silence";
  case VadState::ConfirmingEnd:
    return "confirming_end";
  case VadState::FallbackFixedWindow:
    return "fallback_fixed_window";
  case VadState::Complete:
    return "complete";
  }
  return "unknown";
}

const char *captureExitReasonToString(const CaptureExitReason reason) {
  switch (reason) {
  case CaptureExitReason::FixedWindow:
    return "fixed_window";
  case CaptureExitReason::EndOfSpeech:
    return "end";
  case CaptureExitReason::FallbackNoSpeech:
    return "fallback";
  case CaptureExitReason::MaxCapture:
    return "max_capture";
  }
  return "unknown";
}

void logLine(const String &message) { Serial.println("[bringup] " + message); }

void logStatusSummary() {
  Serial.printf(
      "[status] state=%s wifi=%s cloud=%s error=%s ip=%s session=%s\n",
      deviceStateToString(g_state),
      g_wifiConnected ? "connected" : "disconnected",
      g_cloudReachable ? "reachable" : "unreachable",
      errorCodeToString(g_lastError),
      WiFi.localIP().toString().c_str(),
      g_config.sessionId.c_str());
  Serial.printf("[playback] result=%s format=%s rate=%lu channels=%u bytes=%u\n",
                g_lastPlaybackResult.c_str(),
                g_lastPlaybackAudioFormat.c_str(),
                static_cast<unsigned long>(g_lastPlaybackSampleRateHz),
                g_lastPlaybackChannels,
                static_cast<unsigned int>(g_lastPlaybackPcmBytes));
}

void transitionTo(const DeviceState nextState, const String &reason = String()) {
  g_state = nextState;
  if (reason.isEmpty()) {
    logLine("state -> " + String(deviceStateToString(nextState)));
  } else {
    logLine("state -> " + String(deviceStateToString(nextState)) + " | " + reason);
  }
}

void setError(const ErrorCode code, const String &detail) {
  g_lastError = code;
  g_lastErrorDetail = detail;
  transitionTo(DeviceState::Error, String(errorCodeToString(code)) + " | " + detail);
}

void clearError() {
  g_lastError = ErrorCode::None;
  g_lastErrorDetail = "";
}

String escapeHtml(const String &input) {
  String output;
  output.reserve(input.length() + 16);
  for (size_t i = 0; i < input.length(); ++i) {
    const char c = input.charAt(i);
    switch (c) {
    case '&':
      output += "&amp;";
      break;
    case '<':
      output += "&lt;";
      break;
    case '>':
      output += "&gt;";
      break;
    case '"':
      output += "&quot;";
      break;
    case '\'':
      output += "&#39;";
      break;
    default:
      output += c;
      break;
    }
  }
  return output;
}

String escapeJson(const String &input) {
  String output;
  output.reserve(input.length() + 16);
  for (size_t i = 0; i < input.length(); ++i) {
    const char c = input.charAt(i);
    switch (c) {
    case '\\':
      output += "\\\\";
      break;
    case '"':
      output += "\\\"";
      break;
    case '\n':
      output += "\\n";
      break;
    case '\r':
      output += "\\r";
      break;
    case '\t':
      output += "\\t";
      break;
    default:
      output += c;
      break;
    }
  }
  return output;
}

String encodeBase64(const uint8_t *data, const size_t length) {
  static const char table[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

  String encoded;
  encoded.reserve(((length + 2) / 3) * 4);

  for (size_t index = 0; index < length; index += 3) {
    const uint32_t octetA = data[index];
    const uint32_t octetB = (index + 1 < length) ? data[index + 1] : 0;
    const uint32_t octetC = (index + 2 < length) ? data[index + 2] : 0;
    const uint32_t triple = (octetA << 16U) | (octetB << 8U) | octetC;

    encoded += table[(triple >> 18U) & 0x3FU];
    encoded += table[(triple >> 12U) & 0x3FU];
    encoded += (index + 1 < length) ? table[(triple >> 6U) & 0x3FU] : '=';
    encoded += (index + 2 < length) ? table[triple & 0x3FU] : '=';
  }

  return encoded;
}

size_t base64EncodedLength(const size_t inputLength) {
  return ((inputLength + 2) / 3) * 4;
}

int8_t decodeBase64Char(const char value) {
  if (value >= 'A' && value <= 'Z') {
    return value - 'A';
  }
  if (value >= 'a' && value <= 'z') {
    return value - 'a' + 26;
  }
  if (value >= '0' && value <= '9') {
    return value - '0' + 52;
  }
  if (value == '+') {
    return 62;
  }
  if (value == '/') {
    return 63;
  }
  if (value == '=') {
    return -2;
  }
  return -1;
}

bool decodeBase64(const String &encoded, uint8_t **decodedBytes, size_t *decodedLength) {
  const size_t inputLength = encoded.length();
  if (inputLength == 0 || inputLength % 4 != 0) {
    return false;
  }

  size_t padding = 0;
  if (inputLength >= 1 && encoded.charAt(inputLength - 1) == '=') {
    ++padding;
  }
  if (inputLength >= 2 && encoded.charAt(inputLength - 2) == '=') {
    ++padding;
  }

  const size_t outputLength = (inputLength / 4) * 3 - padding;
  uint8_t *buffer = static_cast<uint8_t *>(malloc(outputLength > 0 ? outputLength : 1));
  if (buffer == nullptr) {
    return false;
  }

  size_t outputIndex = 0;
  for (size_t index = 0; index < inputLength; index += 4) {
    const int8_t value0 = decodeBase64Char(encoded.charAt(index));
    const int8_t value1 = decodeBase64Char(encoded.charAt(index + 1));
    const int8_t value2 = decodeBase64Char(encoded.charAt(index + 2));
    const int8_t value3 = decodeBase64Char(encoded.charAt(index + 3));
    if (value0 < 0 || value1 < 0 || value2 == -1 || value3 == -1) {
      free(buffer);
      return false;
    }

    const uint32_t sextet0 = static_cast<uint32_t>(value0);
    const uint32_t sextet1 = static_cast<uint32_t>(value1);
    const uint32_t sextet2 = value2 >= 0 ? static_cast<uint32_t>(value2) : 0;
    const uint32_t sextet3 = value3 >= 0 ? static_cast<uint32_t>(value3) : 0;
    const uint32_t triple =
        (sextet0 << 18U) | (sextet1 << 12U) | (sextet2 << 6U) | sextet3;

    if (outputIndex < outputLength) {
      buffer[outputIndex++] = static_cast<uint8_t>((triple >> 16U) & 0xFFU);
    }
    if (outputIndex < outputLength && value2 != -2) {
      buffer[outputIndex++] = static_cast<uint8_t>((triple >> 8U) & 0xFFU);
    }
    if (outputIndex < outputLength && value3 != -2) {
      buffer[outputIndex++] = static_cast<uint8_t>(triple & 0xFFU);
    }
  }

  *decodedBytes = buffer;
  *decodedLength = outputLength;
  return true;
}

uint16_t readLe16(const uint8_t *data) {
  return static_cast<uint16_t>(data[0]) |
         static_cast<uint16_t>(static_cast<uint16_t>(data[1]) << 8U);
}

uint32_t readLe32(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) |
         (static_cast<uint32_t>(data[1]) << 8U) |
         (static_cast<uint32_t>(data[2]) << 16U) |
         (static_cast<uint32_t>(data[3]) << 24U);
}

bool writeClientBuffer(Client &client, const uint8_t *data, size_t length) {
  while (length > 0) {
    const size_t written = client.write(data, length);
    if (written == 0) {
      return false;
    }
    data += written;
    length -= written;
    yield();
  }
  return true;
}

bool writeClientString(Client &client, const String &value) {
  return writeClientBuffer(client,
                           reinterpret_cast<const uint8_t *>(value.c_str()),
                           value.length());
}

bool writeBase64ToClient(Client &client, const uint8_t *data, const size_t length) {
  static const char table[] =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

  char chunk[4];
  for (size_t index = 0; index < length; index += 3) {
    const uint32_t octetA = data[index];
    const uint32_t octetB = (index + 1 < length) ? data[index + 1] : 0;
    const uint32_t octetC = (index + 2 < length) ? data[index + 2] : 0;
    const uint32_t triple = (octetA << 16U) | (octetB << 8U) | octetC;

    chunk[0] = table[(triple >> 18U) & 0x3FU];
    chunk[1] = table[(triple >> 12U) & 0x3FU];
    chunk[2] = (index + 1 < length) ? table[(triple >> 6U) & 0x3FU] : '=';
    chunk[3] = (index + 2 < length) ? table[triple & 0x3FU] : '=';

    if (!writeClientBuffer(client, reinterpret_cast<const uint8_t *>(chunk), sizeof(chunk))) {
      return false;
    }
  }
  return true;
}

bool parseWavePcm(const uint8_t *audioBytes,
                  const size_t audioByteCount,
                  ParsedWavePcm *parsedWave,
                  String *errorDetail) {
  if (audioByteCount < 44) {
    *errorDetail = "decoded audio is too small to be a WAV file";
    return false;
  }
  if (memcmp(audioBytes, "RIFF", 4) != 0 || memcmp(audioBytes + 8, "WAVE", 4) != 0) {
    *errorDetail = "decoded audio is not RIFF/WAVE";
    return false;
  }

  bool sawFormatChunk = false;
  bool sawDataChunk = false;
  size_t offset = 12;
  while (offset + 8 <= audioByteCount) {
    const uint8_t *chunk = audioBytes + offset;
    const uint32_t chunkSize = readLe32(chunk + 4);
    size_t resolvedChunkSize = static_cast<size_t>(chunkSize);
    const size_t chunkDataOffset = offset + 8;
    const bool isDataChunk = memcmp(chunk, "data", 4) == 0;
    if (chunkDataOffset > audioByteCount) {
      *errorDetail = "wav chunk exceeds decoded payload length";
      return false;
    }
    if (resolvedChunkSize == 0xFFFFFFFFU && isDataChunk) {
      resolvedChunkSize = audioByteCount - chunkDataOffset;
    } else if (chunkDataOffset + resolvedChunkSize > audioByteCount) {
      if (isDataChunk) {
        // Some streamed/provider-generated WAVs leave the data chunk size as unknown.
        resolvedChunkSize = audioByteCount - chunkDataOffset;
      } else {
        *errorDetail = "wav chunk exceeds decoded payload length";
        return false;
      }
    }

    if (memcmp(chunk, "fmt ", 4) == 0) {
      if (resolvedChunkSize < 16) {
        *errorDetail = "wav fmt chunk is too small";
        return false;
      }
      const uint8_t *fmt = audioBytes + chunkDataOffset;
      parsedWave->audioFormat = readLe16(fmt);
      parsedWave->channelCount = readLe16(fmt + 2);
      parsedWave->sampleRateHz = readLe32(fmt + 4);
      parsedWave->bitsPerSample = readLe16(fmt + 14);
      sawFormatChunk = true;
    } else if (isDataChunk) {
      parsedWave->pcmData = audioBytes + chunkDataOffset;
      parsedWave->pcmByteCount = resolvedChunkSize;
      sawDataChunk = true;
    }

    offset = chunkDataOffset + resolvedChunkSize;
    if ((resolvedChunkSize & 0x1U) != 0U) {
      ++offset;
    }
  }

  if (!sawFormatChunk) {
    *errorDetail = "wav fmt chunk is missing";
    return false;
  }
  if (!sawDataChunk || parsedWave->pcmData == nullptr || parsedWave->pcmByteCount == 0) {
    *errorDetail = "wav data chunk is missing";
    return false;
  }
  if (parsedWave->audioFormat != 1) {
    *errorDetail = "wav audio format is not PCM";
    return false;
  }
  if (parsedWave->sampleRateHz == 0) {
    *errorDetail = "wav sample rate is invalid";
    return false;
  }
  return true;
}

void loadConfig() {
  g_config.ssid = trimCopy(g_preferences.getString(kPrefsKeySsid, ""));
  g_config.password = g_preferences.getString(kPrefsKeyPassword, "");
  g_config.cloudBaseUrl =
      trimCopy(g_preferences.getString(kPrefsKeyCloudBaseUrl, kDefaultCloudBaseUrl));
  g_config.sessionId = trimCopy(g_preferences.getString(kPrefsKeySessionId, ""));
  g_config.deviceId = trimCopy(g_preferences.getString(kPrefsKeyDeviceId, ""));
  g_config.locale = trimCopy(g_preferences.getString(kPrefsKeyLocale, kDefaultLocale));

  if (g_config.deviceId.isEmpty()) {
    g_config.deviceId = defaultDeviceId();
  }
  if (g_config.locale.isEmpty()) {
    g_config.locale = kDefaultLocale;
  }
}

void saveConfig(const RuntimeConfig &config) {
  g_preferences.putString(kPrefsKeySsid, config.ssid);
  g_preferences.putString(kPrefsKeyPassword, config.password);
  g_preferences.putString(kPrefsKeyCloudBaseUrl, config.cloudBaseUrl);
  g_preferences.putString(kPrefsKeySessionId, config.sessionId);
  g_preferences.putString(kPrefsKeyDeviceId, config.deviceId);
  g_preferences.putString(kPrefsKeyLocale, config.locale);
  loadConfig();
}

void clearStoredConfig() {
  g_preferences.remove(kPrefsKeySsid);
  g_preferences.remove(kPrefsKeyPassword);
  g_preferences.remove(kPrefsKeyCloudBaseUrl);
  g_preferences.remove(kPrefsKeySessionId);
  g_preferences.remove(kPrefsKeyDeviceId);
  g_preferences.remove(kPrefsKeyLocale);
  loadConfig();
}

String buildPairingPage() {
  String html;
  html.reserve(2600);
  html += F("<!DOCTYPE html><html><head><meta charset='utf-8'>");
  html += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  html += F("<title>AI Pet Bring-up</title>");
  html += F("<style>body{font-family:Arial,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;}");
  html += F("label{display:block;font-weight:600;margin-top:12px;}input{width:100%;padding:10px;margin-top:6px;box-sizing:border-box;}");
  html += F("button{margin-top:16px;padding:10px 16px;}code{background:#f4f4f4;padding:2px 4px;}small{color:#555;}");
  html += F("</style></head><body>");
  html += F("<h1>XIAO ESP32S3 Sense Bring-up</h1>");
  html += "<p>State: <strong>" + String(deviceStateToString(g_state)) + "</strong></p>";
  html += "<p>Last error: <strong>" + String(errorCodeToString(g_lastError)) + "</strong></p>";
  html += "<p>Pairing AP: <code>" + escapeHtml(g_pairingApSsid) + "</code></p>";
  html += F("<form method='POST' action='/save'>");
  html += "<label>Wi-Fi SSID<input name='ssid' value='" + escapeHtml(g_config.ssid) + "' required></label>";
  html += "<label>Wi-Fi Password<input name='password' type='password' value='" +
          escapeHtml(g_config.password) + "'></label>";
  html += "<label>Cloud Base URL<input name='cloudBaseUrl' value='" +
          escapeHtml(g_config.cloudBaseUrl) + "' required></label>";
  html += "<label>Session ID<input name='sessionId' value='" + escapeHtml(g_config.sessionId) +
          "' required></label>";
  html += "<label>Device ID<input name='deviceId' value='" + escapeHtml(g_config.deviceId) +
          "' required></label>";
  html += "<label>Locale<input name='locale' value='" + escapeHtml(g_config.locale) + "'></label>";
  html += F("<button type='submit'>Save And Reconnect</button></form>");
  html += F("<form method='POST' action='/clear'><button type='submit'>Clear Stored Config</button></form>");
  html += F("<p><small>Playback is enabled for MAX98357 on GPIO7/GPIO8/GPIO9. Trigger a full turn from serial with <code>listen</code>.</small></p>");
  html += F("</body></html>");
  return html;
}

void handleRootPage() { g_server.send(200, "text/html", buildPairingPage()); }

void handleStatusPage() {
  StaticJsonDocument<512> doc;
  doc["state"] = deviceStateToString(g_state);
  doc["lastError"] = errorCodeToString(g_lastError);
  doc["wifiConnected"] = g_wifiConnected;
  doc["cloudReachable"] = g_cloudReachable;
  doc["ip"] = WiFi.localIP().toString();
  doc["sessionId"] = g_config.sessionId;
  doc["deviceId"] = g_config.deviceId;
  doc["locale"] = g_config.locale;
  String payload;
  serializeJson(doc, payload);
  g_server.send(200, "application/json", payload);
}

void startPairingPortal(const String &reason) {
  if (g_pairingPortalActive) {
    transitionTo(DeviceState::PairingReady, reason);
    return;
  }

  WiFi.mode(WIFI_AP_STA);
  g_pairingApSsid = "AI-PET-SETUP-" + chipSuffix();
  WiFi.softAP(g_pairingApSsid.c_str(), kPairingApPassword);
  g_server.begin();
  g_pairingPortalActive = true;
  transitionTo(DeviceState::PairingReady, reason);
  logLine("pairing portal ready at http://192.168.4.1/");
}

void stopPairingPortal() {
  if (!g_pairingPortalActive) {
    return;
  }

  g_server.stop();
  WiFi.softAPdisconnect(true);
  g_pairingPortalActive = false;
  WiFi.mode(WIFI_STA);
}

void handleSaveConfig() {
  RuntimeConfig nextConfig;
  nextConfig.ssid = trimCopy(g_server.arg("ssid"));
  nextConfig.password = g_server.arg("password");
  nextConfig.cloudBaseUrl = trimCopy(g_server.arg("cloudBaseUrl"));
  nextConfig.sessionId = trimCopy(g_server.arg("sessionId"));
  nextConfig.deviceId = trimCopy(g_server.arg("deviceId"));
  nextConfig.locale = trimCopy(g_server.arg("locale"));

  if (nextConfig.deviceId.isEmpty()) {
    nextConfig.deviceId = defaultDeviceId();
  }
  if (nextConfig.locale.isEmpty()) {
    nextConfig.locale = kDefaultLocale;
  }

  saveConfig(nextConfig);
  g_reconnectRequested = true;
  clearError();
  g_server.send(
      200,
      "text/html",
      "<html><body><h1>Saved</h1><p>Config stored. Watch the serial log for reconnect status.</p></body></html>");
}

void handleClearConfig() {
  clearStoredConfig();
  g_wifiConnected = false;
  g_cloudReachable = false;
  clearError();
  WiFi.disconnect(true, true);
  startPairingPortal("config cleared, waiting for pairing");
  g_server.send(200, "text/html",
                "<html><body><h1>Cleared</h1><p>Stored config removed.</p></body></html>");
}

void configureWebRoutes() {
  g_server.on("/", HTTP_GET, handleRootPage);
  g_server.on("/status", HTTP_GET, handleStatusPage);
  g_server.on("/save", HTTP_POST, handleSaveConfig);
  g_server.on("/clear", HTTP_POST, handleClearConfig);
}

bool parseBaseUrl(const String &rawUrl, ParsedUrl *parsedUrl) {
  const String url = trimCopy(rawUrl);
  const int schemeSeparator = url.indexOf("://");
  if (schemeSeparator <= 0) {
    return false;
  }

  const String scheme = url.substring(0, schemeSeparator);
  const bool secure = scheme.equalsIgnoreCase("https");
  if (!secure && !scheme.equalsIgnoreCase("http")) {
    return false;
  }

  const String remainder = url.substring(schemeSeparator + 3);
  const int slashIndex = remainder.indexOf('/');
  const String hostPort = slashIndex >= 0 ? remainder.substring(0, slashIndex) : remainder;
  const String basePath = slashIndex >= 0 ? remainder.substring(slashIndex) : "";
  if (hostPort.isEmpty()) {
    return false;
  }

  String host = hostPort;
  uint16_t port = secure ? 443 : 80;
  const int colonIndex = hostPort.lastIndexOf(':');
  if (colonIndex > 0) {
    host = hostPort.substring(0, colonIndex);
    const String portText = hostPort.substring(colonIndex + 1);
    if (portText.isEmpty()) {
      return false;
    }
    port = static_cast<uint16_t>(portText.toInt());
    if (port == 0) {
      return false;
    }
  }

  parsedUrl->valid = true;
  parsedUrl->secure = secure;
  parsedUrl->host = host;
  parsedUrl->port = port;
  parsedUrl->basePath = basePath;
  return true;
}

String normalizedCloudBaseUrl() {
  String url = trimCopy(g_config.cloudBaseUrl);
  while (url.endsWith("/")) {
    url.remove(url.length() - 1);
  }
  return url;
}

String buildVoiceLoopUrl() {
  return normalizedCloudBaseUrl() + "/v1/internal/device-sessions/" + g_config.sessionId +
         "/voice-loop";
}

String buildVoiceLoopPath(const ParsedUrl &parsedUrl) {
  String path = parsedUrl.basePath;
  if (path.isEmpty()) {
    path = "";
  }
  while (path.endsWith("/")) {
    path.remove(path.length() - 1);
  }
  path += "/v1/internal/device-sessions/";
  path += g_config.sessionId;
  path += "/voice-loop";
  return path;
}

String buildAudioDownloadPath(const ParsedUrl &parsedUrl) {
  String path = parsedUrl.basePath;
  if (path.isEmpty()) {
    return "/";
  }
  if (!path.startsWith("/")) {
    path = "/" + path;
  }
  return path;
}

bool readHttpResponse(Client &client, int *statusCode, String *body) {
  const uint32_t startedAt = millis();
  while (!client.available() && client.connected() && millis() - startedAt < kHttpTimeoutMs) {
    delay(10);
  }

  if (!client.available()) {
    return false;
  }

  const String statusLine = client.readStringUntil('\n');
  const int firstSpace = statusLine.indexOf(' ');
  if (firstSpace < 0) {
    return false;
  }
  const int secondSpace = statusLine.indexOf(' ', firstSpace + 1);
  const String codeText =
      secondSpace > firstSpace ? statusLine.substring(firstSpace + 1, secondSpace)
                               : statusLine.substring(firstSpace + 1);
  *statusCode = codeText.toInt();
  if (*statusCode <= 0) {
    return false;
  }

  bool isChunked = false;
  int contentLength = -1;
  while (client.connected()) {
    String headerLine = client.readStringUntil('\n');
    headerLine.trim();
    if (headerLine.length() == 0) {
      break;
    }

    const int colonIndex = headerLine.indexOf(':');
    if (colonIndex < 0) {
      continue;
    }

    String headerName = headerLine.substring(0, colonIndex);
    String headerValue = headerLine.substring(colonIndex + 1);
    headerName.trim();
    headerValue.trim();
    headerName.toLowerCase();
    headerValue.toLowerCase();

    if (headerName == "transfer-encoding" && headerValue.indexOf("chunked") >= 0) {
      isChunked = true;
    } else if (headerName == "content-length") {
      contentLength = headerValue.toInt();
    }
  }

  if (isChunked) {
    body->reserve(1024);
    while (true) {
      String chunkSizeLine = client.readStringUntil('\n');
      chunkSizeLine.trim();
      const int semicolonIndex = chunkSizeLine.indexOf(';');
      if (semicolonIndex >= 0) {
        chunkSizeLine = chunkSizeLine.substring(0, semicolonIndex);
      }
      const size_t chunkSize = strtoul(chunkSizeLine.c_str(), nullptr, 16);
      if (chunkSize == 0) {
        while (client.connected()) {
          String trailerLine = client.readStringUntil('\n');
          trailerLine.trim();
          if (trailerLine.length() == 0) {
            break;
          }
        }
        return true;
      }

      size_t remaining = chunkSize;
      const uint32_t chunkStartedAt = millis();
      while (remaining > 0) {
        if (!client.available()) {
          if (!client.connected() || millis() - chunkStartedAt >= kHttpTimeoutMs) {
            return false;
          }
          delay(1);
          continue;
        }

        body->concat(static_cast<char>(client.read()));
        --remaining;
      }

      if (client.available() || client.connected()) {
        client.readStringUntil('\n');
      }
    }
  }

  if (contentLength >= 0) {
    body->reserve(contentLength);
    size_t remaining = static_cast<size_t>(contentLength);
    const uint32_t bodyStartedAt = millis();
    while (remaining > 0) {
      if (!client.available()) {
        if (!client.connected() || millis() - bodyStartedAt >= kHttpTimeoutMs) {
          return false;
        }
        delay(1);
        continue;
      }
      body->concat(static_cast<char>(client.read()));
      --remaining;
    }
    return true;
  }

  body->reserve(1024);
  const uint32_t bodyStartedAt = millis();
  while (client.connected() || client.available()) {
    while (client.available()) {
      body->concat(static_cast<char>(client.read()));
    }
    if (!client.connected()) {
      break;
    }
    if (millis() - bodyStartedAt >= kHttpTimeoutMs) {
      break;
    }
    delay(10);
  }

  return true;
}

bool readClientExact(Client &client, uint8_t *buffer, const size_t length) {
  size_t offset = 0;
  uint32_t lastReadAt = millis();
  while (offset < length) {
    if (!client.available()) {
      if (!client.connected() || millis() - lastReadAt >= kHttpTimeoutMs) {
        return false;
      }
      delay(1);
      continue;
    }

    const int value = client.read();
    if (value < 0) {
      continue;
    }

    buffer[offset++] = static_cast<uint8_t>(value);
    lastReadAt = millis();
  }
  return true;
}

bool skipClientBytes(Client &client, const size_t length) {
  size_t skipped = 0;
  uint32_t lastReadAt = millis();
  while (skipped < length) {
    if (!client.available()) {
      if (!client.connected() || millis() - lastReadAt >= kHttpTimeoutMs) {
        return false;
      }
      delay(1);
      continue;
    }

    const int value = client.read();
    if (value < 0) {
      continue;
    }

    ++skipped;
    lastReadAt = millis();
  }
  return true;
}

bool readHttpResponseHeaders(Client &client, HttpResponseMetadata *metadata) {
  metadata->statusCode = 0;
  metadata->chunked = false;
  metadata->contentLength = -1;
  metadata->contentType = "";

  const uint32_t startedAt = millis();
  while (!client.available() && client.connected() && millis() - startedAt < kHttpTimeoutMs) {
    delay(10);
  }

  if (!client.available()) {
    return false;
  }

  const String statusLine = client.readStringUntil('\n');
  const int firstSpace = statusLine.indexOf(' ');
  if (firstSpace < 0) {
    return false;
  }
  const int secondSpace = statusLine.indexOf(' ', firstSpace + 1);
  const String codeText =
      secondSpace > firstSpace ? statusLine.substring(firstSpace + 1, secondSpace)
                               : statusLine.substring(firstSpace + 1);
  metadata->statusCode = codeText.toInt();
  if (metadata->statusCode <= 0) {
    return false;
  }

  while (client.connected()) {
    String headerLine = client.readStringUntil('\n');
    headerLine.trim();
    if (headerLine.length() == 0) {
      break;
    }

    const int colonIndex = headerLine.indexOf(':');
    if (colonIndex < 0) {
      continue;
    }

    String headerName = headerLine.substring(0, colonIndex);
    String headerValue = headerLine.substring(colonIndex + 1);
    headerName.trim();
    headerValue.trim();

    String normalizedHeaderName = headerName;
    normalizedHeaderName.toLowerCase();
    String normalizedHeaderValue = headerValue;
    normalizedHeaderValue.toLowerCase();

    if (normalizedHeaderName == "transfer-encoding" &&
        normalizedHeaderValue.indexOf("chunked") >= 0) {
      metadata->chunked = true;
    } else if (normalizedHeaderName == "content-length") {
      metadata->contentLength = headerValue.toInt();
    } else if (normalizedHeaderName == "content-type") {
      metadata->contentType = headerValue;
    }
  }

  return true;
}

bool readHttpBinaryResponse(Client &client,
                            int *statusCode,
                            uint8_t **bodyBytes,
                            size_t *bodyLength,
                            String *contentType) {
  *bodyBytes = nullptr;
  *bodyLength = 0;
  *contentType = "";

  HttpResponseMetadata metadata;
  if (!readHttpResponseHeaders(client, &metadata)) {
    return false;
  }
  *statusCode = metadata.statusCode;
  *contentType = metadata.contentType;

  if (metadata.chunked || metadata.contentLength < 0) {
    return false;
  }

  uint8_t *buffer =
      static_cast<uint8_t *>(malloc(static_cast<size_t>(metadata.contentLength)));
  if (buffer == nullptr) {
    return false;
  }

  size_t offset = 0;
  const uint32_t bodyStartedAt = millis();
  while (offset < static_cast<size_t>(metadata.contentLength)) {
    if (!client.available()) {
      if (!client.connected() || millis() - bodyStartedAt >= kHttpTimeoutMs) {
        free(buffer);
        return false;
      }
      delay(1);
      continue;
    }

    const int value = client.read();
    if (value < 0) {
      continue;
    }
    buffer[offset++] = static_cast<uint8_t>(value);
  }

  *bodyBytes = buffer;
  *bodyLength = static_cast<size_t>(metadata.contentLength);
  return true;
}

bool executeHttpGetBinary(const ParsedUrl &parsedUrl,
                          const String &path,
                          int *statusCode,
                          uint8_t **bodyBytes,
                          size_t *bodyLength,
                          String *contentType) {
  if (parsedUrl.secure) {
    if (kCloudCaCertPem == nullptr && !kAllowInsecureHttps) {
      setError(ErrorCode::TlsConfigRequired,
               "HTTPS request blocked because no CA certificate is configured");
      return false;
    }

    WiFiClientSecure client;
    client.setTimeout(kHttpTimeoutMs);
    if (kCloudCaCertPem != nullptr) {
      client.setCACert(kCloudCaCertPem);
    } else {
      client.setInsecure();
    }
    if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
      setError(ErrorCode::CloudRequestFailed, "TLS connect failed before GET");
      return false;
    }

    client.printf("GET %s HTTP/1.1\r\n", path.c_str());
    client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
    client.print("Connection: close\r\n\r\n");

    const bool ok = readHttpBinaryResponse(client, statusCode, bodyBytes, bodyLength, contentType);
    client.stop();
    if (!ok) {
      setError(ErrorCode::CloudRequestFailed, "failed to read HTTPS binary response");
      return false;
    }
    return true;
  }

  WiFiClient client;
  client.setTimeout(kHttpTimeoutMs);
  if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
    setError(ErrorCode::CloudRequestFailed, "TCP connect failed before GET");
    return false;
  }

  client.printf("GET %s HTTP/1.1\r\n", path.c_str());
  client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
  client.print("Connection: close\r\n\r\n");

  const bool ok = readHttpBinaryResponse(client, statusCode, bodyBytes, bodyLength, contentType);
  client.stop();
  if (!ok) {
    setError(ErrorCode::CloudRequestFailed, "failed to read HTTP binary response");
    return false;
  }
  return true;
}

bool executeHttpJsonPost(const ParsedUrl &parsedUrl,
                         const String &path,
                         const String &payload,
                         int *statusCode,
                         String *body) {
  if (parsedUrl.secure) {
    if (kCloudCaCertPem == nullptr && !kAllowInsecureHttps) {
      setError(ErrorCode::TlsConfigRequired,
               "HTTPS request blocked because no CA certificate is configured");
      return false;
    }

    WiFiClientSecure client;
    client.setTimeout(kHttpTimeoutMs);
    if (kCloudCaCertPem != nullptr) {
      client.setCACert(kCloudCaCertPem);
    } else {
      client.setInsecure();
    }
    if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
      setError(ErrorCode::CloudRequestFailed, "TLS connect failed before POST");
      return false;
    }

    client.printf("POST %s HTTP/1.1\r\n", path.c_str());
    client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
    client.print("Content-Type: application/json\r\n");
    client.print("Connection: close\r\n");
    client.printf("Content-Length: %u\r\n\r\n", payload.length());
    client.print(payload);

    const bool ok = readHttpResponse(client, statusCode, body);
    client.stop();
    if (!ok) {
      setError(ErrorCode::CloudRequestFailed, "failed to read HTTPS response");
      return false;
    }
    return true;
  }

  WiFiClient client;
  client.setTimeout(kHttpTimeoutMs);
  if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
    setError(ErrorCode::CloudRequestFailed, "TCP connect failed before POST");
    return false;
  }

  client.printf("POST %s HTTP/1.1\r\n", path.c_str());
  client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
  client.print("Content-Type: application/json\r\n");
  client.print("Connection: close\r\n");
  client.printf("Content-Length: %u\r\n\r\n", payload.length());
  client.print(payload);

  const bool ok = readHttpResponse(client, statusCode, body);
  client.stop();
  if (!ok) {
    setError(ErrorCode::CloudRequestFailed, "failed to read HTTP response");
    return false;
  }
  return true;
}

bool executeHttpJsonPostWithBase64Audio(const ParsedUrl &parsedUrl,
                                        const String &path,
                                        const String &jsonPrefix,
                                        const uint8_t *audioBytes,
                                        const size_t audioByteCount,
                                        const String &jsonSuffix,
                                        int *statusCode,
                                        String *body) {
  const size_t contentLength =
      jsonPrefix.length() + base64EncodedLength(audioByteCount) + jsonSuffix.length();

  auto sendRequest = [&](Client &client) -> bool {
    client.printf("POST %s HTTP/1.1\r\n", path.c_str());
    client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
    client.print("Content-Type: application/json\r\n");
    client.print("Connection: close\r\n");
    client.printf("Content-Length: %u\r\n\r\n", static_cast<unsigned int>(contentLength));

    if (!writeClientString(client, jsonPrefix)) {
      return false;
    }
    if (!writeBase64ToClient(client, audioBytes, audioByteCount)) {
      return false;
    }
    if (!writeClientString(client, jsonSuffix)) {
      return false;
    }
    return true;
  };

  if (parsedUrl.secure) {
    if (kCloudCaCertPem == nullptr && !kAllowInsecureHttps) {
      setError(ErrorCode::TlsConfigRequired,
               "HTTPS request blocked because no CA certificate is configured");
      return false;
    }

    WiFiClientSecure client;
    client.setTimeout(kHttpTimeoutMs);
    if (kCloudCaCertPem != nullptr) {
      client.setCACert(kCloudCaCertPem);
    } else {
      client.setInsecure();
    }
    if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
      setError(ErrorCode::CloudRequestFailed, "TLS connect failed before POST");
      return false;
    }

    if (!sendRequest(client)) {
      client.stop();
      setError(ErrorCode::CloudRequestFailed, "failed to stream HTTPS request body");
      return false;
    }

    const bool ok = readHttpResponse(client, statusCode, body);
    client.stop();
    if (!ok) {
      setError(ErrorCode::CloudRequestFailed, "failed to read HTTPS response");
      return false;
    }
    return true;
  }

  WiFiClient client;
  client.setTimeout(kHttpTimeoutMs);
  if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
    setError(ErrorCode::CloudRequestFailed, "TCP connect failed before POST");
    return false;
  }

  if (!sendRequest(client)) {
    client.stop();
    setError(ErrorCode::CloudRequestFailed, "failed to stream HTTP request body");
    return false;
  }

  const bool ok = readHttpResponse(client, statusCode, body);
  client.stop();
  if (!ok) {
    setError(ErrorCode::CloudRequestFailed, "failed to read HTTP response");
    return false;
  }
  return true;
}

bool probeCloudTransport() {
  ParsedUrl parsedUrl;
  if (!parseBaseUrl(g_config.cloudBaseUrl, &parsedUrl)) {
    setError(ErrorCode::ConfigMissing, "cloudBaseUrl is invalid");
    return false;
  }

  transitionTo(DeviceState::ConnectingCloud, "probing cloud transport");

  if (parsedUrl.secure) {
    if (kCloudCaCertPem == nullptr && !kAllowInsecureHttps) {
      setError(ErrorCode::TlsConfigRequired,
               "HTTPS endpoint configured without CA certificate or insecure override");
      return false;
    }

    WiFiClientSecure secureClient;
    secureClient.setTimeout(kCloudConnectTimeoutMs);
    if (kCloudCaCertPem != nullptr) {
      secureClient.setCACert(kCloudCaCertPem);
    } else {
      secureClient.setInsecure();
    }
    const bool connected = secureClient.connect(parsedUrl.host.c_str(), parsedUrl.port);
    secureClient.stop();
    if (!connected) {
      setError(ErrorCode::CloudProbeFailed, "TLS transport connect failed");
      return false;
    }
  } else {
    WiFiClient client;
    client.setTimeout(kCloudConnectTimeoutMs);
    const bool connected = client.connect(parsedUrl.host.c_str(), parsedUrl.port);
    client.stop();
    if (!connected) {
      setError(ErrorCode::CloudProbeFailed, "TCP transport connect failed");
      return false;
    }
  }

  g_cloudReachable = true;
  clearError();
  transitionTo(DeviceState::ReadyToSpeak, "cloud transport reachable");
  return true;
}

bool connectWiFi() {
  if (!g_config.hasWiFiCredentials()) {
    startPairingPortal("missing Wi-Fi credentials");
    return false;
  }

  clearError();
  transitionTo(DeviceState::ConnectingWiFi, "joining " + g_config.ssid);

  stopPairingPortal();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.disconnect(true, true);
  delay(100);
  WiFi.begin(g_config.ssid.c_str(), g_config.password.c_str());

  const uint32_t startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < kWifiConnectTimeoutMs) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    g_wifiConnected = false;
    g_cloudReachable = false;
    setError(ErrorCode::WiFiConnectFailed, "timed out while joining configured network");
    startPairingPortal("Wi-Fi connect failed, waiting for updated config");
    return false;
  }

  g_wifiConnected = true;
  clearError();
  transitionTo(DeviceState::WiFiConnected, "ip=" + WiFi.localIP().toString());
  return true;
}

bool ensureConnectivityReady() {
  if (!g_config.hasWiFiCredentials() || !g_config.hasCloudConfig()) {
    startPairingPortal("missing Wi-Fi or cloud config");
    return false;
  }
  if (!g_wifiConnected && !connectWiFi()) {
    return false;
  }
  if (!g_cloudReachable && !probeCloudTransport()) {
    return false;
  }
  if (g_state != DeviceState::ReadyToSpeak) {
    transitionTo(DeviceState::ReadyToSpeak, "connectivity ready");
  }
  return true;
}

bool initializeMicrophone() {
  if (g_micInitialized) {
    return true;
  }

#if AI_PET_USE_ESP_I2S
  g_i2s.setPinsPdmRx(kPdmClockPin, kPdmDataPin);
  const bool began = g_i2s.begin(I2S_MODE_PDM_RX,
                                 kAudioSampleRateHz,
                                 I2S_DATA_BIT_WIDTH_16BIT,
                                 I2S_SLOT_MODE_MONO);
#else
  I2S.setAllPins(-1, kPdmClockPin, kPdmDataPin, -1, -1);
  const bool began = I2S.begin(PDM_MONO_MODE, kAudioSampleRateHz, 16);
#endif

  if (!began) {
    setError(ErrorCode::MicInitFailed, "Arduino I2S begin failed");
    return false;
  }

  g_micInitialized = true;
  logLine("microphone ready on GPIO41/GPIO42");
  return true;
}

bool initializePlayback() {
  if (!kEnablePlayback) {
    return true;
  }
  if (g_playbackInitialized) {
    return true;
  }

#if AI_PET_USE_ESP_I2S
  const i2s_data_bit_width_t playbackBitsConfig =
      kPlaybackBitsPerSample == 16 ? I2S_DATA_BIT_WIDTH_16BIT : I2S_DATA_BIT_WIDTH_16BIT;
  const i2s_slot_mode_t playbackSlotMode =
      kPlaybackChannels == 1 ? I2S_SLOT_MODE_MONO : I2S_SLOT_MODE_STEREO;
  g_playbackI2s.setPins(kPlaybackBclkPin, kPlaybackLrclkPin, kPlaybackDinPin);
  const bool began = g_playbackI2s.begin(I2S_MODE_STD,
                                         kPlaybackDefaultSampleRateHz,
                                         playbackBitsConfig,
                                         playbackSlotMode);
#else
  const bool began = false;
#endif

  if (!began) {
#if AI_PET_USE_ESP_I2S
    setError(ErrorCode::PlaybackInitFailed, "MAX98357 I2S TX init failed");
#else
    setError(ErrorCode::PlaybackInitFailed,
             "MAX98357 playback requires ESP32 Arduino core >= 3 with ESP_I2S");
#endif
    g_lastPlaybackResult = "failed";
    return false;
  }

  g_playbackInitialized = true;
  logLine("playback ready on MAX98357 BCLK=" + String(kPlaybackBclkPin) +
          " LRC=" + String(kPlaybackLrclkPin) + " DIN=" + String(kPlaybackDinPin));
  return true;
}

bool configurePlaybackFormat(const uint32_t sampleRateHz) {
#if AI_PET_USE_ESP_I2S
  return g_playbackI2s.configureTX(sampleRateHz,
                                   I2S_DATA_BIT_WIDTH_16BIT,
                                   I2S_SLOT_MODE_STEREO);
#else
  (void)sampleRateHz;
  return false;
#endif
}

bool writePlaybackChunk(const uint8_t *data, const size_t byteCount) {
#if AI_PET_USE_ESP_I2S
  const size_t written = g_playbackI2s.write(data, byteCount);
  if (written != byteCount) {
    setError(ErrorCode::PlaybackWriteFailed,
             "I2S write short write expected=" + String(byteCount) +
                 " actual=" + String(written) +
                 " err=" + String(g_playbackI2s.lastError()));
    g_lastPlaybackResult = "failed";
    return false;
  }
  return true;
#else
  (void)data;
  (void)byteCount;
  setError(ErrorCode::PlaybackWriteFailed, "I2S TX write is unavailable on this core");
  g_lastPlaybackResult = "failed";
  return false;
#endif
}

bool preparePlaybackForWave(const ParsedWavePcm &parsedWave) {
  if (!initializePlayback()) {
    return false;
  }
  if (parsedWave.bitsPerSample != 16) {
    setError(ErrorCode::PlaybackUnsupported,
             "only PCM16 WAV is supported, got bitsPerSample=" +
                 String(parsedWave.bitsPerSample));
    g_lastPlaybackResult = "unsupported";
    return false;
  }
  if (parsedWave.channelCount != 1 && parsedWave.channelCount != 2) {
    setError(ErrorCode::PlaybackUnsupported,
             "only mono/stereo WAV is supported, got channels=" +
                 String(parsedWave.channelCount));
    g_lastPlaybackResult = "unsupported";
    return false;
  }
  if ((parsedWave.pcmByteCount % (parsedWave.channelCount * sizeof(int16_t))) != 0) {
    setError(ErrorCode::PlaybackDecodeFailed, "wav pcm byte count is not frame-aligned");
    g_lastPlaybackResult = "failed";
    return false;
  }
  if (!configurePlaybackFormat(parsedWave.sampleRateHz)) {
    setError(ErrorCode::PlaybackInitFailed,
             "failed to configure I2S TX for sampleRateHz=" +
                 String(parsedWave.sampleRateHz));
    g_lastPlaybackResult = "failed";
    return false;
  }

  g_lastPlaybackSampleRateHz = parsedWave.sampleRateHz;
  g_lastPlaybackChannels = 2;
  g_lastPlaybackPcmBytes = parsedWave.channelCount == 2
                               ? parsedWave.pcmByteCount
                               : (parsedWave.pcmByteCount * 2);
  return true;
}

bool playParsedWave(const ParsedWavePcm &parsedWave) {
  if (!preparePlaybackForWave(parsedWave)) {
    return false;
  }

  const uint32_t startedAt = millis();
  if (parsedWave.channelCount == 2) {
    size_t written = 0;
    while (written < parsedWave.pcmByteCount) {
      const size_t chunkBytes =
          min(kPlaybackWriteChunkBytes, parsedWave.pcmByteCount - written);
      if (!writePlaybackChunk(parsedWave.pcmData + written, chunkBytes)) {
        return false;
      }
      written += chunkBytes;
      yield();
    }
  } else {
    constexpr size_t kMonoFramesPerChunk = 256;
    int16_t stereoChunk[kMonoFramesPerChunk * 2];
    const int16_t *monoPcm = reinterpret_cast<const int16_t *>(parsedWave.pcmData);
    size_t framesRemaining = parsedWave.pcmByteCount / sizeof(int16_t);
    size_t frameOffset = 0;
    while (framesRemaining > 0) {
      const size_t frameCount = min(kMonoFramesPerChunk, framesRemaining);
      for (size_t index = 0; index < frameCount; ++index) {
        const int16_t sample = monoPcm[frameOffset + index];
        stereoChunk[index * 2] = sample;
        stereoChunk[index * 2 + 1] = sample;
      }
      if (!writePlaybackChunk(reinterpret_cast<const uint8_t *>(stereoChunk),
                              frameCount * sizeof(int16_t) * 2)) {
        return false;
      }
      frameOffset += frameCount;
      framesRemaining -= frameCount;
      yield();
    }
  }

  g_lastPlaybackResult = "succeeded";
  logLine("playback done durationMs=" + String(millis() - startedAt) +
          " sampleRateHz=" + String(parsedWave.sampleRateHz) +
          " inputChannels=" + String(parsedWave.channelCount) +
          " outputChannels=2 pcmBytes=" + String(g_lastPlaybackPcmBytes));
  return true;
}

bool streamWavePcmFromClient(Client &client,
                             const int contentLength,
                             ParsedWavePcm *parsedWave,
                             String *errorDetail) {
  if (contentLength >= 0 && contentLength < 44) {
    *errorDetail = "streamed audio is too small to be a WAV file";
    return false;
  }

  uint8_t riffHeader[12];
  if (!readClientExact(client, riffHeader, sizeof(riffHeader))) {
    setError(ErrorCode::CloudRequestFailed, "timed out while reading WAV header");
    g_lastPlaybackResult = "failed";
    return false;
  }
  if (memcmp(riffHeader, "RIFF", 4) != 0 || memcmp(riffHeader + 8, "WAVE", 4) != 0) {
    *errorDetail = "streamed audio is not RIFF/WAVE";
    return false;
  }

  bool sawFormatChunk = false;
  size_t bodyBytesRead = sizeof(riffHeader);
  while (contentLength < 0 || bodyBytesRead + 8 <= static_cast<size_t>(contentLength)) {
    uint8_t chunkHeader[8];
    if (!readClientExact(client, chunkHeader, sizeof(chunkHeader))) {
      setError(ErrorCode::CloudRequestFailed, "timed out while reading WAV chunk header");
      g_lastPlaybackResult = "failed";
      return false;
    }
    bodyBytesRead += sizeof(chunkHeader);

    const uint32_t chunkSize = readLe32(chunkHeader + 4);
    size_t resolvedChunkSize = static_cast<size_t>(chunkSize);
    const bool isDataChunk = memcmp(chunkHeader, "data", 4) == 0;
    if (chunkSize == 0xFFFFFFFFU && isDataChunk) {
      if (contentLength < 0 || bodyBytesRead > static_cast<size_t>(contentLength)) {
        *errorDetail = "streamed wav data chunk length is invalid";
        return false;
      }
      resolvedChunkSize = static_cast<size_t>(contentLength) - bodyBytesRead;
    } else if (contentLength >= 0) {
      const size_t remaining = bodyBytesRead <= static_cast<size_t>(contentLength)
                                   ? static_cast<size_t>(contentLength) - bodyBytesRead
                                   : 0;
      if (resolvedChunkSize > remaining) {
        if (isDataChunk) {
          resolvedChunkSize = remaining;
        } else {
          *errorDetail = "streamed wav chunk exceeds payload length";
          return false;
        }
      }
    }

    if (memcmp(chunkHeader, "fmt ", 4) == 0) {
      if (resolvedChunkSize < 16) {
        *errorDetail = "wav fmt chunk is too small";
        return false;
      }

      uint8_t fmtChunk[16];
      if (!readClientExact(client, fmtChunk, sizeof(fmtChunk))) {
        setError(ErrorCode::CloudRequestFailed, "timed out while reading WAV fmt chunk");
        g_lastPlaybackResult = "failed";
        return false;
      }
      bodyBytesRead += sizeof(fmtChunk);

      parsedWave->audioFormat = readLe16(fmtChunk);
      parsedWave->channelCount = readLe16(fmtChunk + 2);
      parsedWave->sampleRateHz = readLe32(fmtChunk + 4);
      parsedWave->bitsPerSample = readLe16(fmtChunk + 14);
      sawFormatChunk = true;

      const size_t remainingFmtBytes = resolvedChunkSize - sizeof(fmtChunk);
      if (remainingFmtBytes > 0) {
        if (!skipClientBytes(client, remainingFmtBytes)) {
          setError(ErrorCode::CloudRequestFailed, "timed out while skipping WAV fmt extension");
          g_lastPlaybackResult = "failed";
          return false;
        }
        bodyBytesRead += remainingFmtBytes;
      }
    } else if (isDataChunk) {
      parsedWave->pcmByteCount = resolvedChunkSize;
      if (!sawFormatChunk) {
        *errorDetail = "wav fmt chunk must appear before data";
        return false;
      }
      logLine("wav parsed sampleRateHz=" + String(parsedWave->sampleRateHz) +
              " bitsPerSample=" + String(parsedWave->bitsPerSample) +
              " channels=" + String(parsedWave->channelCount) +
              " pcmBytes=" + String(parsedWave->pcmByteCount));
      if (!preparePlaybackForWave(*parsedWave)) {
        return false;
      }

      const uint32_t startedAt = millis();
      if (parsedWave->channelCount == 2) {
        uint8_t playbackChunk[kPlaybackWriteChunkBytes];
        size_t remainingPcmBytes = resolvedChunkSize;
        while (remainingPcmBytes > 0) {
          size_t chunkBytes = min(sizeof(playbackChunk), remainingPcmBytes);
          const size_t frameBytes = parsedWave->channelCount * sizeof(int16_t);
          if ((chunkBytes % frameBytes) != 0 && chunkBytes != remainingPcmBytes) {
            chunkBytes -= chunkBytes % frameBytes;
          }
          if (!readClientExact(client, playbackChunk, chunkBytes)) {
            setError(ErrorCode::CloudRequestFailed, "timed out while streaming WAV PCM data");
            g_lastPlaybackResult = "failed";
            return false;
          }
          if (!writePlaybackChunk(playbackChunk, chunkBytes)) {
            return false;
          }
          remainingPcmBytes -= chunkBytes;
          bodyBytesRead += chunkBytes;
          yield();
        }
      } else {
        constexpr size_t kMonoFramesPerChunk = 256;
        int16_t monoChunk[kMonoFramesPerChunk];
        int16_t stereoChunk[kMonoFramesPerChunk * 2];
        size_t remainingPcmBytes = resolvedChunkSize;
        while (remainingPcmBytes > 0) {
          size_t chunkBytes = min(sizeof(monoChunk), remainingPcmBytes);
          if ((chunkBytes % sizeof(int16_t)) != 0 && chunkBytes != remainingPcmBytes) {
            chunkBytes -= chunkBytes % sizeof(int16_t);
          }
          if (!readClientExact(client,
                               reinterpret_cast<uint8_t *>(monoChunk),
                               chunkBytes)) {
            setError(ErrorCode::CloudRequestFailed, "timed out while streaming WAV PCM data");
            g_lastPlaybackResult = "failed";
            return false;
          }

          const size_t frameCount = chunkBytes / sizeof(int16_t);
          for (size_t index = 0; index < frameCount; ++index) {
            const int16_t sample = monoChunk[index];
            stereoChunk[index * 2] = sample;
            stereoChunk[index * 2 + 1] = sample;
          }
          if (!writePlaybackChunk(reinterpret_cast<const uint8_t *>(stereoChunk),
                                  frameCount * sizeof(int16_t) * 2)) {
            return false;
          }
          remainingPcmBytes -= chunkBytes;
          bodyBytesRead += chunkBytes;
          yield();
        }
      }

      g_lastPlaybackResult = "succeeded";
      logLine("playback done durationMs=" + String(millis() - startedAt) +
              " sampleRateHz=" + String(parsedWave->sampleRateHz) +
              " inputChannels=" + String(parsedWave->channelCount) +
              " outputChannels=2 pcmBytes=" + String(g_lastPlaybackPcmBytes));
      return true;
    } else {
      if (!skipClientBytes(client, resolvedChunkSize)) {
        setError(ErrorCode::CloudRequestFailed, "timed out while skipping WAV chunk");
        g_lastPlaybackResult = "failed";
        return false;
      }
      bodyBytesRead += resolvedChunkSize;
    }

    if ((resolvedChunkSize & 0x1U) != 0U) {
      uint8_t padding = 0;
      if (!readClientExact(client, &padding, 1)) {
        setError(ErrorCode::CloudRequestFailed, "timed out while reading WAV chunk padding");
        g_lastPlaybackResult = "failed";
        return false;
      }
      ++bodyBytesRead;
    }
  }

  *errorDetail = "wav data chunk is missing";
  return false;
}

bool streamCloudAudioResponse(Client &client,
                              const String &audioUrl,
                              const String &fallbackAudioFormat) {
  HttpResponseMetadata metadata;
  if (!readHttpResponseHeaders(client, &metadata)) {
    setError(ErrorCode::CloudRequestFailed, "failed to read HTTP binary response");
    return false;
  }
  if (metadata.statusCode >= 400) {
    setError(ErrorCode::CloudRequestFailed,
             "audio download failed with status=" + String(metadata.statusCode));
    return false;
  }
  if (metadata.chunked) {
    setError(ErrorCode::CloudRequestFailed, "chunked audio download is not supported yet");
    return false;
  }

  const String resolvedAudioFormat =
      metadata.contentType.isEmpty() ? fallbackAudioFormat : metadata.contentType;
  g_lastPlaybackAudioFormat = resolvedAudioFormat.isEmpty() ? "unknown" : resolvedAudioFormat;
  if (!resolvedAudioFormat.isEmpty() && !resolvedAudioFormat.equalsIgnoreCase("audio/wav")) {
    setError(ErrorCode::PlaybackUnsupported,
             "cloud audioFormat is not supported for playback: " + resolvedAudioFormat);
    g_lastPlaybackResult = "unsupported";
    return false;
  }

  logLine("streaming cloud audio url=" + audioUrl +
          " bytes=" + String(metadata.contentLength) +
          " contentType=" + (metadata.contentType.isEmpty() ? String("<empty>") : metadata.contentType));

  ParsedWavePcm parsedWave;
  String errorDetail;
  if (!streamWavePcmFromClient(client, metadata.contentLength, &parsedWave, &errorDetail)) {
    if (!errorDetail.isEmpty() && g_lastError == ErrorCode::None) {
      setError(ErrorCode::PlaybackDecodeFailed, errorDetail);
      g_lastPlaybackResult = "failed";
    }
    return false;
  }
  return true;
}

bool streamCloudAudioFromUrl(const CloudResponseSummary &summary) {
  if (summary.audioUrl.isEmpty()) {
    return false;
  }

  ParsedUrl parsedUrl;
  String path;
  if (summary.audioUrl.startsWith("http://") || summary.audioUrl.startsWith("https://")) {
    if (!parseBaseUrl(summary.audioUrl, &parsedUrl)) {
      setError(ErrorCode::CloudRequestFailed, "audioUrl is invalid");
      return false;
    }
    path = buildAudioDownloadPath(parsedUrl);
  } else {
    if (!parseBaseUrl(g_config.cloudBaseUrl, &parsedUrl)) {
      setError(ErrorCode::ConfigMissing, "cloudBaseUrl is invalid");
      return false;
    }
    path = summary.audioUrl.startsWith("/") ? summary.audioUrl : "/" + summary.audioUrl;
  }

  if (parsedUrl.secure) {
    if (kCloudCaCertPem == nullptr && !kAllowInsecureHttps) {
      setError(ErrorCode::TlsConfigRequired,
               "HTTPS request blocked because no CA certificate is configured");
      return false;
    }

    WiFiClientSecure client;
    client.setTimeout(kHttpTimeoutMs);
    if (kCloudCaCertPem != nullptr) {
      client.setCACert(kCloudCaCertPem);
    } else {
      client.setInsecure();
    }
    if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
      setError(ErrorCode::CloudRequestFailed, "TLS connect failed before GET");
      return false;
    }

    client.printf("GET %s HTTP/1.1\r\n", path.c_str());
    client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
    client.print("Connection: close\r\n\r\n");

    const bool ok = streamCloudAudioResponse(client, summary.audioUrl, summary.audioFormat);
    client.stop();
    return ok;
  }

  WiFiClient client;
  client.setTimeout(kHttpTimeoutMs);
  if (!client.connect(parsedUrl.host.c_str(), parsedUrl.port)) {
    setError(ErrorCode::CloudRequestFailed, "TCP connect failed before GET");
    return false;
  }

  client.printf("GET %s HTTP/1.1\r\n", path.c_str());
  client.printf("Host: %s:%u\r\n", parsedUrl.host.c_str(), parsedUrl.port);
  client.print("Connection: close\r\n\r\n");

  const bool ok = streamCloudAudioResponse(client, summary.audioUrl, summary.audioFormat);
  client.stop();
  return ok;
}

bool downloadCloudAudioBytes(const CloudResponseSummary &summary,
                             uint8_t **audioBytes,
                             size_t *audioByteCount,
                             String *resolvedAudioFormat) {
  if (summary.audioUrl.isEmpty()) {
    return false;
  }

  ParsedUrl parsedUrl;
  String path;
  if (summary.audioUrl.startsWith("http://") || summary.audioUrl.startsWith("https://")) {
    if (!parseBaseUrl(summary.audioUrl, &parsedUrl)) {
      setError(ErrorCode::CloudRequestFailed, "audioUrl is invalid");
      return false;
    }
    path = buildAudioDownloadPath(parsedUrl);
  } else {
    if (!parseBaseUrl(g_config.cloudBaseUrl, &parsedUrl)) {
      setError(ErrorCode::ConfigMissing, "cloudBaseUrl is invalid");
      return false;
    }
    path = summary.audioUrl.startsWith("/") ? summary.audioUrl : "/" + summary.audioUrl;
  }

  int statusCode = 0;
  String contentType;
  if (!executeHttpGetBinary(parsedUrl, path, &statusCode, audioBytes, audioByteCount, &contentType)) {
    return false;
  }
  if (statusCode >= 400) {
    if (*audioBytes != nullptr) {
      free(*audioBytes);
      *audioBytes = nullptr;
      *audioByteCount = 0;
    }
    setError(ErrorCode::CloudRequestFailed,
             "audio download failed with status=" + String(statusCode));
    return false;
  }

  *resolvedAudioFormat = summary.audioFormat;
  if (resolvedAudioFormat->isEmpty()) {
    *resolvedAudioFormat = contentType;
  }

  logLine("downloaded cloud audio url=" + summary.audioUrl +
          " bytes=" + String(*audioByteCount) +
          " contentType=" + (contentType.isEmpty() ? String("<empty>") : contentType));
  return true;
}

bool playCloudAudio(const CloudResponseSummary &summary) {
  g_lastPlaybackAudioFormat = summary.audioFormat.isEmpty() ? "unknown" : summary.audioFormat;
  g_lastPlaybackResult = "decoding";
  g_lastPlaybackSampleRateHz = 0;
  g_lastPlaybackChannels = 0;
  g_lastPlaybackPcmBytes = 0;

  uint8_t *decodedAudio = nullptr;
  size_t decodedAudioLength = 0;
  String resolvedAudioFormat = summary.audioFormat;

  if (!summary.audioUrl.isEmpty()) {
    if (!streamCloudAudioFromUrl(summary)) {
      g_lastPlaybackResult = "failed";
      return false;
    }
    return true;
  } else if (!summary.audioBase64.isEmpty()) {
    if (!decodeBase64(summary.audioBase64, &decodedAudio, &decodedAudioLength)) {
      setError(ErrorCode::PlaybackDecodeFailed, "audioBase64 could not be decoded");
      g_lastPlaybackResult = "failed";
      return false;
    }

    logLine("decoded cloud audio format=" + g_lastPlaybackAudioFormat +
            " base64Bytes=" + String(summary.audioBase64.length()) +
            " decodedBytes=" + String(decodedAudioLength));
  } else {
    setError(ErrorCode::CloudAudioMissing, "cloud response did not include audioBase64 or audioUrl");
    g_lastPlaybackResult = "missing";
    return false;
  }

  if (!resolvedAudioFormat.isEmpty() && !resolvedAudioFormat.equalsIgnoreCase("audio/wav")) {
    setError(ErrorCode::PlaybackUnsupported,
             "cloud audioFormat is not supported for playback: " + resolvedAudioFormat);
    g_lastPlaybackResult = "unsupported";
    if (decodedAudio != nullptr) {
      free(decodedAudio);
    }
    return false;
  }

  ParsedWavePcm parsedWave;
  String errorDetail;
  const bool parsed = parseWavePcm(decodedAudio, decodedAudioLength, &parsedWave, &errorDetail);
  if (!parsed) {
    free(decodedAudio);
    setError(ErrorCode::PlaybackDecodeFailed, errorDetail);
    g_lastPlaybackResult = "failed";
    return false;
  }

  logLine("wav parsed sampleRateHz=" + String(parsedWave.sampleRateHz) +
          " bitsPerSample=" + String(parsedWave.bitsPerSample) +
          " channels=" + String(parsedWave.channelCount) +
          " pcmBytes=" + String(parsedWave.pcmByteCount));

  const bool played = playParsedWave(parsedWave);
  free(decodedAudio);
  return played;
}

void releaseCapturedAudio(CapturedAudio *capturedAudio) {
  if (capturedAudio->samples != nullptr) {
    free(capturedAudio->samples);
    capturedAudio->samples = nullptr;
  }
  capturedAudio->byteCount = 0;
  capturedAudio->sampleCount = 0;
  capturedAudio->durationMs = 0;
  capturedAudio->strategy = CaptureStrategy::FixedWindow;
  capturedAudio->exitReason = CaptureExitReason::FixedWindow;
  capturedAudio->speechDetected = false;
}

bool readPdmSamples(int16_t *destination,
                    const size_t sampleCount,
                    uint32_t *lastBytesReadAt) {
  size_t index = 0;
  while (index < sampleCount) {
    int sample = -1;
#if AI_PET_USE_ESP_I2S
    sample = g_i2s.read();
#else
    sample = I2S.read();
#endif

    if (sample < 0) {
      if (millis() - *lastBytesReadAt >= kAudioCaptureStallTimeoutMs) {
        setError(ErrorCode::MicCaptureFailed, "timed out waiting for PDM microphone data");
        return false;
      }
      delay(1);
      continue;
    }

    destination[index] = static_cast<int16_t>(sample);
    *lastBytesReadAt = millis();
    ++index;
    yield();
  }
  return true;
}

uint32_t computeFrameEnergy(const int16_t *samples, const size_t sampleCount) {
  if (sampleCount == 0) {
    return 0;
  }

  int64_t sum = 0;
  for (size_t index = 0; index < sampleCount; ++index) {
    sum += samples[index];
  }
  const int32_t mean = static_cast<int32_t>(sum / static_cast<int64_t>(sampleCount));

  uint64_t deviationSum = 0;
  for (size_t index = 0; index < sampleCount; ++index) {
    const int32_t centered = static_cast<int32_t>(samples[index]) - mean;
    deviationSum += centered >= 0 ? centered : -centered;
  }

  return static_cast<uint32_t>(deviationSum / sampleCount);
}

uint32_t updateNoiseFloor(const uint32_t currentFloor, const uint32_t frameEnergy) {
  if (currentFloor == 0) {
    return max(frameEnergy, static_cast<uint32_t>(1));
  }
  return max(static_cast<uint32_t>((currentFloor * 7 + frameEnergy) / 8),
             static_cast<uint32_t>(1));
}

void logVadStateTransition(const VadState state, const String &detail = String()) {
  if (detail.isEmpty()) {
    logLine("vad state -> " + String(vadStateToString(state)));
    return;
  }
  logLine("vad state -> " + String(vadStateToString(state)) + " | " + detail);
}

bool captureAudioFixedWindow(CapturedAudio *capturedAudio) {
  const size_t targetByteCount =
      (kAudioSampleRateHz * kAudioCaptureMs / 1000) * sizeof(int16_t);
  const size_t targetSampleCount = targetByteCount / sizeof(int16_t);

  logLine("capture strategy=" + String(captureStrategyToString(CaptureStrategy::FixedWindow)) +
          " durationMs=" + String(kAudioCaptureMs) +
          " expectedBytes=" + String(targetByteCount) +
          " expectedSamples=" + String(targetSampleCount));

  capturedAudio->samples = static_cast<int16_t *>(malloc(targetByteCount));
  if (capturedAudio->samples == nullptr) {
    setError(ErrorCode::MicCaptureFailed, "malloc failed for fixed capture buffer");
    return false;
  }

  memset(capturedAudio->samples, 0, targetByteCount);

  const uint32_t startedAt = millis();
  uint32_t lastBytesReadAt = startedAt;
  if (!readPdmSamples(capturedAudio->samples, targetSampleCount, &lastBytesReadAt)) {
    releaseCapturedAudio(capturedAudio);
    return false;
  }

  capturedAudio->sampleCount = targetSampleCount;
  capturedAudio->byteCount = targetByteCount;
  capturedAudio->durationMs = millis() - startedAt;
  capturedAudio->strategy = CaptureStrategy::FixedWindow;
  capturedAudio->exitReason = CaptureExitReason::FixedWindow;
  capturedAudio->speechDetected = true;
  logLine("captured durationMs=" + String(capturedAudio->durationMs) +
          " bytes=" + String(capturedAudio->byteCount) +
          " samples=" + String(capturedAudio->sampleCount));
  return true;
}

bool captureAudioLightweightVad(CapturedAudio *capturedAudio) {
  const size_t maxByteCount = kVadMaxSampleCount * sizeof(int16_t);
  capturedAudio->samples = static_cast<int16_t *>(malloc(maxByteCount));
  if (capturedAudio->samples == nullptr) {
    setError(ErrorCode::MicCaptureFailed, "malloc failed for vad capture buffer");
    return false;
  }

  memset(capturedAudio->samples, 0, maxByteCount);

  logLine("capture strategy=" +
          String(captureStrategyToString(CaptureStrategy::LightweightVad)) +
          " frameMs=" + String(kVadFrameMs) + " minMs=" + String(kVadMinCaptureMs) +
          " maxMs=" + String(kVadMaxCaptureMs) +
          " fallbackFixedMs=" + String(kAudioCaptureMs));

  VadState vadState = VadState::Priming;
  logVadStateTransition(vadState, "measuring ambient noise floor");
  CaptureExitReason exitReason = CaptureExitReason::MaxCapture;

  uint32_t lastBytesReadAt = millis();
  size_t totalSamplesRead = 0;
  size_t speechStartSampleIndex = 0;
  size_t bootstrapFramesCollected = 0;
  uint32_t bootstrapEnergySum = 0;
  uint32_t noiseFloor = 0;
  uint32_t trailingSilenceMs = 0;
  uint32_t consecutiveSpeechFrames = 0;
  uint32_t consecutiveResumeFrames = 0;
  uint32_t tailWindowStartedAtMs = 0;
  uint32_t confirmWindowStartedAtMs = 0;
  bool speechDetected = false;

  while (totalSamplesRead + kVadFrameSampleCount <= kVadMaxSampleCount) {
    int16_t *frameStart = capturedAudio->samples + totalSamplesRead;
    if (!readPdmSamples(frameStart, kVadFrameSampleCount, &lastBytesReadAt)) {
      releaseCapturedAudio(capturedAudio);
      return false;
    }

    totalSamplesRead += kVadFrameSampleCount;
    const uint32_t totalCaptureMs = (totalSamplesRead * 1000) / kAudioSampleRateHz;
    const uint32_t frameEnergy = computeFrameEnergy(frameStart, kVadFrameSampleCount);

    if (vadState == VadState::Priming) {
      bootstrapEnergySum += frameEnergy;
      ++bootstrapFramesCollected;
      if (bootstrapFramesCollected >= kVadBootstrapFrameCount) {
        noiseFloor =
            max(static_cast<uint32_t>(bootstrapEnergySum / bootstrapFramesCollected),
                static_cast<uint32_t>(1));
        vadState = VadState::WaitingForSpeech;
        logVadStateTransition(vadState, "noiseFloor=" + String(noiseFloor));
      }
      continue;
    }

    const uint32_t startThreshold =
        max(kVadStartFloorAbs,
            static_cast<uint32_t>((noiseFloor * kVadStartRatioNum) / kVadStartRatioDen) +
                kVadStartOffsetAbs);
    const uint32_t endThreshold =
        max(kVadEndFloorAbs,
            static_cast<uint32_t>((noiseFloor * kVadEndRatioNum) / kVadEndRatioDen) +
                kVadEndOffsetAbs);
    const uint32_t resumeThreshold = endThreshold + kVadResumeOffsetAbs;

    if (!speechDetected) {
      if (frameEnergy >= startThreshold) {
        ++consecutiveSpeechFrames;
      } else {
        consecutiveSpeechFrames = 0;
        noiseFloor = updateNoiseFloor(noiseFloor, frameEnergy);
      }

      if (consecutiveSpeechFrames >= kVadStartTriggerFrames) {
        speechDetected = true;
        const size_t triggerLookbackSamples =
            kVadPreRollSampleCount + (kVadStartTriggerFrames * kVadFrameSampleCount);
        speechStartSampleIndex =
            totalSamplesRead > triggerLookbackSamples ? totalSamplesRead - triggerLookbackSamples
                                                      : 0;
        vadState = VadState::Speaking;
        logVadStateTransition(
            vadState,
            "frameEnergy=" + String(frameEnergy) + " noiseFloor=" + String(noiseFloor) +
                " startThreshold=" + String(startThreshold) +
                " speechStartMs=" +
                String((speechStartSampleIndex * 1000) / kAudioSampleRateHz));
      } else if (totalCaptureMs >= kAudioCaptureMs) {
        vadState = VadState::FallbackFixedWindow;
        exitReason = CaptureExitReason::FallbackNoSpeech;
        logVadStateTransition(vadState,
                              "no speech detected before fallback baseline window");
        break;
      }
      continue;
    }

    const uint32_t speechDurationMs =
        ((totalSamplesRead - speechStartSampleIndex) * 1000) / kAudioSampleRateHz;

    if (frameEnergy <= endThreshold) {
      consecutiveResumeFrames = 0;
      trailingSilenceMs += kVadFrameMs;
      if (vadState != VadState::TrailingSilence) {
        if (vadState == VadState::Speaking) {
          tailWindowStartedAtMs = totalCaptureMs;
          confirmWindowStartedAtMs = 0;
          vadState = VadState::TrailingSilence;
          logVadStateTransition(vadState,
                                "frameEnergy=" + String(frameEnergy) +
                                    " endThreshold=" + String(endThreshold));
        }
      }
      if (vadState == VadState::TrailingSilence &&
          speechDurationMs >= kVadMinCaptureMs &&
          trailingSilenceMs >= kVadEndSilenceMs) {
        vadState = VadState::ConfirmingEnd;
        confirmWindowStartedAtMs = totalCaptureMs;
        logVadStateTransition(vadState,
                              "trailingSilenceMs=" + String(trailingSilenceMs) +
                                  " confirmMs=" + String(kVadEndConfirmMs));
      }
      if (vadState == VadState::ConfirmingEnd &&
          confirmWindowStartedAtMs > 0 &&
          totalCaptureMs >= confirmWindowStartedAtMs + kVadEndConfirmMs) {
        vadState = VadState::Complete;
        exitReason = CaptureExitReason::EndOfSpeech;
        logVadStateTransition(vadState,
                              "reason=end_of_speech_confirmed speechDurationMs=" +
                                  String(speechDurationMs) +
                                  " trailingSilenceMs=" + String(trailingSilenceMs) +
                                  " confirmMs=" + String(kVadEndConfirmMs));
        break;
      }
    } else if ((vadState == VadState::TrailingSilence || vadState == VadState::ConfirmingEnd) &&
               frameEnergy < resumeThreshold) {
      consecutiveResumeFrames = 0;
    } else {
      ++consecutiveResumeFrames;
      if (vadState != VadState::TrailingSilence && vadState != VadState::ConfirmingEnd) {
        trailingSilenceMs = 0;
        consecutiveResumeFrames = 0;
      } else if (consecutiveResumeFrames >= kVadResumeTriggerFrames) {
        trailingSilenceMs = 0;
        consecutiveResumeFrames = 0;
        confirmWindowStartedAtMs = 0;
        tailWindowStartedAtMs = 0;
        vadState = VadState::Speaking;
        logVadStateTransition(vadState,
                              "speech resumed frameEnergy=" + String(frameEnergy) +
                                  " resumeThreshold=" + String(resumeThreshold) +
                                  " trailingSilenceMs=" + String(trailingSilenceMs));
      }
    }

    if (speechDurationMs >= kVadMinCaptureMs && trailingSilenceMs >= kVadEndSilenceMs) {
      if (vadState == VadState::ConfirmingEnd &&
          confirmWindowStartedAtMs > 0 &&
          totalCaptureMs >= confirmWindowStartedAtMs + kVadEndConfirmMs) {
        vadState = VadState::Complete;
        exitReason = CaptureExitReason::EndOfSpeech;
        logVadStateTransition(vadState,
                              "reason=end_of_speech_confirmed speechDurationMs=" +
                                  String(speechDurationMs) +
                                  " trailingSilenceMs=" + String(trailingSilenceMs) +
                                  " confirmMs=" + String(kVadEndConfirmMs));
        break;
      }
    }

    if (vadState == VadState::ConfirmingEnd &&
        speechDurationMs >= kVadMinCaptureMs &&
        trailingSilenceMs >= kVadPostSpeechGuardMinSilenceMs &&
        tailWindowStartedAtMs > 0 &&
        totalCaptureMs >= tailWindowStartedAtMs + kVadPostSpeechMaxMs) {
      vadState = VadState::Complete;
      exitReason = CaptureExitReason::EndOfSpeech;
      logVadStateTransition(vadState,
                            "reason=end_of_speech_guard speechDurationMs=" +
                                String(speechDurationMs) +
                                " trailingSilenceMs=" + String(trailingSilenceMs) +
                                " guardMinSilenceMs=" +
                                String(kVadPostSpeechGuardMinSilenceMs) +
                                " tailWindowMs=" +
                                String(totalCaptureMs - tailWindowStartedAtMs));
      break;
    }

    if ((vadState == VadState::TrailingSilence || vadState == VadState::ConfirmingEnd) &&
        speechDurationMs >= kVadMinCaptureMs &&
        trailingSilenceMs >= kVadNearMaxEndSilenceMs &&
        totalCaptureMs + kVadNearMaxWindowMs >= kVadMaxCaptureMs) {
      vadState = VadState::Complete;
      exitReason = CaptureExitReason::EndOfSpeech;
      logVadStateTransition(vadState,
                            "reason=end_of_speech_near_max_capture speechDurationMs=" +
                                String(speechDurationMs) +
                                " trailingSilenceMs=" + String(trailingSilenceMs) +
                                " nearMaxWindowMs=" + String(kVadNearMaxWindowMs));
      break;
    }

    if (totalCaptureMs >= kVadMaxCaptureMs) {
      vadState = VadState::Complete;
      exitReason = CaptureExitReason::MaxCapture;
      logVadStateTransition(vadState,
                            "reason=max_capture totalCaptureMs=" + String(totalCaptureMs));
      break;
    }
  }

  size_t finalStartSampleIndex = 0;
  size_t finalSampleCount = totalSamplesRead;
  if (speechDetected) {
    finalStartSampleIndex = speechStartSampleIndex;
    finalSampleCount = totalSamplesRead - speechStartSampleIndex;
  }

  if (finalSampleCount == 0) {
    releaseCapturedAudio(capturedAudio);
    setError(ErrorCode::MicCaptureFailed, "captured zero samples");
    return false;
  }

  if (speechDetected && finalStartSampleIndex > 0) {
    memmove(capturedAudio->samples,
            capturedAudio->samples + finalStartSampleIndex,
            finalSampleCount * sizeof(int16_t));
  }

  capturedAudio->sampleCount = finalSampleCount;
  capturedAudio->byteCount = finalSampleCount * sizeof(int16_t);
  capturedAudio->durationMs = (finalSampleCount * 1000) / kAudioSampleRateHz;
  capturedAudio->strategy = CaptureStrategy::LightweightVad;
  capturedAudio->exitReason = exitReason;
  capturedAudio->speechDetected = speechDetected;
  logLine("captured durationMs=" + String(capturedAudio->durationMs) +
          " bytes=" + String(capturedAudio->byteCount) +
          " samples=" + String(capturedAudio->sampleCount) +
          " speechDetected=" + String(speechDetected ? "true" : "false"));
  return true;
}

bool captureAudio(CapturedAudio *capturedAudio) {
  if (!initializeMicrophone()) {
    return false;
  }

  if (kEnableLightweightVad) {
    return captureAudioLightweightVad(capturedAudio);
  }
  return captureAudioFixedWindow(capturedAudio);
}

bool parseCloudResponse(const String &body, CloudResponseSummary *summary) {
  const size_t docCapacity =
      max(static_cast<size_t>(8192), body.length() + static_cast<size_t>(1024));
  DynamicJsonDocument doc(docCapacity);
  const auto error = deserializeJson(doc, body);
  if (error) {
    String preview = body.substring(0, 160);
    preview.replace("\r", "\\r");
    preview.replace("\n", "\\n");
    logLine("cloud body preview: " + preview);
    setError(ErrorCode::JsonParseFailed, String("deserializeJson failed: ") + error.c_str());
    return false;
  }

  summary->sessionState = String(static_cast<const char *>(doc["session"]["state"] | "unknown"));
  summary->transcript = String(static_cast<const char *>(doc["transcript"] | ""));
  summary->responseText = String(static_cast<const char *>(doc["responseText"] | ""));
  summary->audioBase64 = String(static_cast<const char *>(doc["audioBase64"] | ""));
  summary->audioFormat = String(static_cast<const char *>(doc["audioFormat"] | ""));
  summary->audioUrl = String(static_cast<const char *>(doc["audioUrl"] | ""));
  summary->fallbackMode = String(static_cast<const char *>(doc["fallbackMode"] | "none"));
  summary->runtimeFailureCode =
      String(static_cast<const char *>(doc["runtimeFailureCode"] | "unknown"));
  return true;
}

bool postVoiceTurn(CapturedAudio *capturedAudio, CloudResponseSummary *summary) {
  const String requestId =
      g_config.deviceId + "-turn-" + String(++g_turnCounter) + "-" + String(millis());
  const uint32_t captureDurationMs = capturedAudio->durationMs;
  const CaptureStrategy captureStrategy = capturedAudio->strategy;
  const CaptureExitReason captureExitReason = capturedAudio->exitReason;
  const bool speechDetected = capturedAudio->speechDetected;
  const uint8_t *audioBytes = reinterpret_cast<const uint8_t *>(capturedAudio->samples);
  const size_t audioByteCount = capturedAudio->byteCount;

  logLine("heap before POST: " + String(ESP.getFreeHeap()));

  String jsonPrefix;
  jsonPrefix.reserve(160);
  jsonPrefix += "{\"requestId\":\"";
  jsonPrefix += escapeJson(requestId);
  jsonPrefix += "\",\"audioBase64\":\"";

  String jsonSuffix;
  jsonSuffix.reserve(128);
  jsonSuffix += "\",\"audioFormat\":\"audio/pcm;codec=s16le;rate=16000;channels=1\"";
  jsonSuffix += ",\"sampleRateHz\":";
  jsonSuffix += String(kAudioSampleRateHz);
  jsonSuffix += ",\"durationMs\":";
  jsonSuffix += String(captureDurationMs);
  jsonSuffix += ",\"locale\":\"";
  jsonSuffix += escapeJson(g_config.locale);
  jsonSuffix += "\"}";

  logLine("post audio bytes=" + String(audioByteCount) +
          " base64Bytes=" + String(base64EncodedLength(audioByteCount)) +
          " contentLength=" +
          String(jsonPrefix.length() + base64EncodedLength(audioByteCount) +
                 jsonSuffix.length()));

  ParsedUrl parsedUrl;
  if (!parseBaseUrl(g_config.cloudBaseUrl, &parsedUrl)) {
    releaseCapturedAudio(capturedAudio);
    setError(ErrorCode::ConfigMissing, "cloudBaseUrl is invalid");
    return false;
  }

  int statusCode = 0;
  String body;
  const String path = buildVoiceLoopPath(parsedUrl);
  if (!executeHttpJsonPostWithBase64Audio(parsedUrl,
                                          path,
                                          jsonPrefix,
                                          audioBytes,
                                          audioByteCount,
                                          jsonSuffix,
                                          &statusCode,
                                          &body)) {
    releaseCapturedAudio(capturedAudio);
    return false;
  }

  releaseCapturedAudio(capturedAudio);

  summary->httpStatus = statusCode;
  const bool parsed = parseCloudResponse(body, summary);
  if (!parsed) {
    return false;
  }

  g_lastSessionState = summary->sessionState;
  g_lastTranscript = summary->transcript;
  g_lastResponseText = summary->responseText;
  g_lastRuntimeFailureCode = summary->runtimeFailureCode;
  g_lastPlaybackAudioFormat = summary->audioFormat.isEmpty() ? "none" : summary->audioFormat;

  logLine("cloud http=" + String(summary->httpStatus) + " session=" + summary->sessionState +
          " fallback=" + summary->fallbackMode + " failure=" + summary->runtimeFailureCode +
          " audioFormat=" + (summary->audioFormat.isEmpty() ? String("<empty>")
                                                             : summary->audioFormat));
  if (!summary->transcript.isEmpty()) {
    logLine("transcript: " + summary->transcript);
  }
  if (!summary->responseText.isEmpty()) {
    logLine("responseText: " + summary->responseText);
  }
  logLine("turn summary | strategy=" + String(captureStrategyToString(captureStrategy)) +
          " durationMs=" + String(captureDurationMs) +
          " exit=" + String(captureExitReasonToString(captureExitReason)) +
          " speechDetected=" + String(speechDetected ? "true" : "false") +
          " transcript=" + (summary->transcript.isEmpty() ? String("<empty>")
                                                          : summary->transcript) +
          " fallback=" + summary->fallbackMode +
          " failure=" + summary->runtimeFailureCode);
  return true;
}

bool runVoiceTurn() {
  if (!ensureConnectivityReady()) {
    return false;
  }

  transitionTo(DeviceState::Listening, "capturing microphone input");
  CapturedAudio capturedAudio;
  if (!captureAudio(&capturedAudio)) {
    return false;
  }

  transitionTo(DeviceState::Thinking, "uploading audio to cloud");
  CloudResponseSummary summary;
  const bool posted = postVoiceTurn(&capturedAudio, &summary);
  if (!posted) {
    return false;
  }

  if (kEnablePlayback) {
    transitionTo(DeviceState::Speaking, "decoding and playing cloud audio");
    if (!playCloudAudio(summary)) {
      return false;
    }
  }

  clearError();
  g_cloudReachable = true;
  transitionTo(DeviceState::ReadyToSpeak,
               kEnablePlayback ? "turn completed with playback" : "turn completed");
  return true;
}

void printHelp() {
  Serial.println("Commands:");
  Serial.println("  help       - show commands");
  Serial.println("  status     - print state and config summary");
  Serial.println("  pairing    - start pairing portal");
  Serial.println("  listen     - capture one turn and upload it");
  Serial.println("  reconnect  - force Wi-Fi and cloud reconnect");
  Serial.println("  clear      - erase stored config and reopen pairing mode");
}

void handleSerialCommand(const String &rawCommand) {
  const String command = trimCopy(rawCommand);
  if (command.isEmpty()) {
    return;
  }

  if (command.equalsIgnoreCase("help")) {
    printHelp();
    return;
  }
  if (command.equalsIgnoreCase("status")) {
    logStatusSummary();
    Serial.printf("[config] ssid=%s cloudBaseUrl=%s deviceId=%s locale=%s\n",
                  g_config.ssid.c_str(),
                  g_config.cloudBaseUrl.c_str(),
                  g_config.deviceId.c_str(),
                  g_config.locale.c_str());
    Serial.printf("[cloud] sessionState=%s runtimeFailure=%s\n", g_lastSessionState.c_str(),
                  g_lastRuntimeFailureCode.c_str());
    if (!g_lastErrorDetail.isEmpty()) {
      Serial.printf("[error-detail] %s\n", g_lastErrorDetail.c_str());
    }
    return;
  }
  if (command.equalsIgnoreCase("pairing")) {
    startPairingPortal("pairing requested over serial");
    return;
  }
  if (command.equalsIgnoreCase("listen")) {
    runVoiceTurn();
    return;
  }
  if (command.equalsIgnoreCase("reconnect")) {
    g_wifiConnected = false;
    g_cloudReachable = false;
    g_reconnectRequested = true;
    logLine("manual reconnect requested");
    return;
  }
  if (command.equalsIgnoreCase("clear")) {
    clearStoredConfig();
    g_wifiConnected = false;
    g_cloudReachable = false;
    WiFi.disconnect(true, true);
    startPairingPortal("config cleared over serial");
    return;
  }

  logLine("unknown command: " + command);
  printHelp();
}

void handleSerialCommands() {
  if (!Serial.available()) {
    return;
  }

  const String command = Serial.readStringUntil('\n');
  handleSerialCommand(command);
}

void maintainConnectivity() {
  const bool currentlyConnected = WiFi.status() == WL_CONNECTED;
  if (currentlyConnected != g_wifiConnected) {
    g_wifiConnected = currentlyConnected;
    if (!currentlyConnected) {
      g_cloudReachable = false;
      if (g_config.hasWiFiCredentials()) {
        transitionTo(DeviceState::ConnectingWiFi, "Wi-Fi link lost, waiting to reconnect");
      }
    }
  }

  if (!g_config.hasWiFiCredentials() || !g_config.hasCloudConfig()) {
    startPairingPortal("waiting for Wi-Fi and cloud config");
    return;
  }

  const bool reconnectDue =
      g_reconnectRequested || millis() - g_lastReconnectAttemptAtMs >= kWifiRetryIntervalMs;

  if ((!g_wifiConnected || !g_cloudReachable) && reconnectDue) {
    g_reconnectRequested = false;
    g_lastReconnectAttemptAtMs = millis();
    if (connectWiFi()) {
      probeCloudTransport();
    }
  }
}

} // namespace

void setup() {
  Serial.begin(kSerialBaud);
  delay(1000);
  Serial.println();
  Serial.println("AI Pet XIAO ESP32S3 Sense bring-up");
  Serial.printf("firmware=%s playback=%s\n", kFirmwareVersion,
                AI_PET_ENABLE_PLAYBACK ? "enabled" : "disabled");

  transitionTo(DeviceState::Booting, "initializing board");

  g_preferences.begin(kPrefsNamespace, false);
  loadConfig();
  configureWebRoutes();

  logLine("deviceId=" + g_config.deviceId);
  logLine("cloudBaseUrl=" + g_config.cloudBaseUrl);

  if (!initializeMicrophone()) {
    return;
  }
  if (kEnablePlayback && !initializePlayback()) {
    return;
  }

  if (!g_config.hasWiFiCredentials() || !g_config.hasCloudConfig()) {
    startPairingPortal("stored config missing");
    printHelp();
    return;
  }

  ensureConnectivityReady();
  printHelp();
}

void loop() {
  if (g_pairingPortalActive) {
    g_server.handleClient();
  }

  handleSerialCommands();
  maintainConnectivity();
  delay(10);
}

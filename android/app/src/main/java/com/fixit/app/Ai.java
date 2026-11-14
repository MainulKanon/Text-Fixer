package com.fixit.app;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * AI provider chain, ported from the Windows app's providers/ package:
 * tries the providers in order (only those with a key), and if a model was retired,
 * picks an available one, retries, and remembers it.
 * Everything here is blocking: call it from a background thread.
 */
final class Ai {
    private Ai() {}

    static class AiException extends Exception {
        AiException(String m) { super(m); }
    }

    static final class ModelGone extends AiException {
        ModelGone(String m) { super(m); }
    }

    static final class Result {
        final String text, provider;
        Result(String text, String provider) { this.text = text; this.provider = provider; }
    }

    private static final int CONNECT_MS = 10_000, READ_MS = 25_000;
    private static final String[] GONE_HINTS = {"does not exist", "not found", "decommission", "deprecated",
            "no longer", "not supported", "do not have access", "no endpoints found", "not a valid model"};
    private static final String[] EXCLUDED = {"whisper", "tts", "guard", "embed", "audio", "image", "transcribe",
            "speech", "moderation", "playai", "orpheus", "compound", "allam", "safeguard"};
    private static final String[] GEMINI_EXCLUDED = {"pro", "omni", "robotics", "computer-use", "customtools",
            "nano", "argon", "exp", "preview", "tts", "image", "live", "embed"};
    private static final String[][] PREFERRED = {
            {"gpt-oss-120b", "llama-3.3-70b", "llama-4", "kimi-k2", "qwen3", "gpt-oss-20b", "70b", "instant"},
            {"gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                    "flash-lite", "flash"},
            {"gpt-oss-120b:free", "llama-3.3-70b-instruct:free", "llama-4-maverick:free", "deepseek", "qwen3", "70b"},
    };
    /** Gemini: thinking level that worked per model ("" = none). Big flash models are slow without "minimal". */
    private static final Map<String, String> GEMINI_LEVEL = new ConcurrentHashMap<>();

    static Result run(Prefs prefs, String system, String user) throws AiException {
        List<String> errors = new ArrayList<>();
        int tried = 0;
        for (String p : prefs.order()) {
            String key = prefs.key(p);
            if (key.isEmpty()) continue;
            tried++;
            int i = Prefs.index(p);
            String model = prefs.model(p);
            try {
                String raw;
                try {
                    raw = complete(p, key, model, system, user);
                } catch (ModelGone gone) {
                    String replacement = pickModel(i, listModels(p, key), model);
                    if (replacement == null) throw new AiException(gone.getMessage() + " – no replacement model found");
                    raw = complete(p, key, replacement, system, user);
                    prefs.setModel(p, replacement);
                }
                String out = clean(raw);
                if (!out.isEmpty()) return new Result(out, Prefs.LABELS[i]);
                errors.add(Prefs.LABELS[i] + ": empty response");
            } catch (AiException e) {
                errors.add(e.getMessage());
            }
        }
        if (tried == 0) throw new AiException("No API key set. Open the Text Fixer app and add a free Groq key.");
        throw new AiException(String.join("\n", errors));
    }

    // ---------------------------------------------------------------- providers
    static String complete(String p, String key, String model, String system, String user) throws AiException {
        try {
            if ("gemini".equals(p)) return gemini(key, model, system, user);
            String url = "groq".equals(p) ? "https://api.groq.com/openai/v1/chat/completions"
                    : "https://openrouter.ai/api/v1/chat/completions";
            JSONObject body = new JSONObject()
                    .put("model", model)
                    .put("temperature", 0.3)
                    .put("messages", new JSONArray()
                            .put(new JSONObject().put("role", "system").put("content", system))
                            .put(new JSONObject().put("role", "user").put("content", user)));
            if ("groq".equals(p) && (model.contains("gpt-oss") || model.contains("qwen3"))) {
                body.put("reasoning_effort", "low");     // much faster for short rewrites
            }
            Resp r = http("POST", url, body.toString(), "Authorization", "Bearer " + key, "X-Title", "Text Fixer");
            check(r, label(p));
            return new JSONObject(r.body).getJSONArray("choices").getJSONObject(0)
                    .getJSONObject("message").optString("content", "");
        } catch (AiException e) {
            throw e;
        } catch (Exception e) {
            throw new AiException(label(p) + ": unexpected response");
        }
    }

    private static String gemini(String key, String model, String system, String user) throws Exception {
        model = model.replaceFirst("^models/", "");
        String known = GEMINI_LEVEL.get(model);
        String[] levels = known != null ? new String[]{known} : new String[]{"minimal", "low", ""};
        Resp r = null;
        for (String level : levels) {
            JSONObject gen = new JSONObject().put("temperature", 0.3);
            if (!level.isEmpty()) gen.put("thinkingConfig", new JSONObject().put("thinkingLevel", level));
            JSONObject body = new JSONObject()
                    .put("systemInstruction", new JSONObject().put("parts", new JSONArray().put(new JSONObject().put("text", system))))
                    .put("contents", new JSONArray().put(new JSONObject().put("role", "user")
                            .put("parts", new JSONArray().put(new JSONObject().put("text", user)))))
                    .put("generationConfig", gen);
            r = http("POST", "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
                    body.toString(), "x-goog-api-key", key);   // key in a header, never in the URL
            if (r.code == 400 && r.body.toLowerCase(Locale.ROOT).contains("thinking")) continue;
            GEMINI_LEVEL.put(model, level);
            break;
        }
        check(r, "Gemini");
        JSONArray parts = new JSONObject(r.body).getJSONArray("candidates").getJSONObject(0)
                .getJSONObject("content").getJSONArray("parts");
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < parts.length(); i++) {
            JSONObject part = parts.getJSONObject(i);
            if (!part.optBoolean("thought")) sb.append(part.optString("text"));
        }
        return sb.toString();
    }

    static List<String> listModels(String p, String key) throws AiException {
        List<String> out = new ArrayList<>();
        try {
            Resp r;
            if ("gemini".equals(p)) {
                r = http("GET", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", null,
                        "x-goog-api-key", key);
                check(r, "Gemini");
                JSONArray arr = new JSONObject(r.body).optJSONArray("models");
                for (int i = 0; arr != null && i < arr.length(); i++) {
                    JSONObject m = arr.getJSONObject(i);
                    String id = m.optString("name").replaceFirst("^models/", "");
                    if (id.startsWith("gemini") && m.optJSONArray("supportedGenerationMethods") != null
                            && m.getJSONArray("supportedGenerationMethods").toString().contains("generateContent")) {
                        out.add(id);
                    }
                }
            } else {
                String url = "groq".equals(p) ? "https://api.groq.com/openai/v1/models" : "https://openrouter.ai/api/v1/models";
                r = http("GET", url, null, "Authorization", "Bearer " + key);
                check(r, label(p));
                JSONArray arr = new JSONObject(r.body).optJSONArray("data");
                for (int i = 0; arr != null && i < arr.length(); i++) {
                    JSONObject m = arr.getJSONObject(i);
                    String id = m.optString("id");
                    if (id.isEmpty() || !m.optBoolean("active", true)) continue;
                    if ("openrouter".equals(p) && !id.endsWith(":free")) continue;
                    out.add(id);
                }
            }
        } catch (AiException e) {
            throw e;
        } catch (Exception e) {
            throw new AiException(label(p) + ": couldn't list models");
        }
        Collections.sort(out);
        return out;
    }

    static String pickModel(int providerIndex, List<String> models, String exclude) {
        String[] excluded = providerIndex == 1 ? GEMINI_EXCLUDED : EXCLUDED;
        List<String> usable = new ArrayList<>();
        for (String m : models) {
            if (m.equals(exclude)) continue;
            String low = m.toLowerCase(Locale.ROOT);
            boolean bad = false;
            for (String w : excluded) if (low.contains(w)) { bad = true; break; }
            if (!bad) usable.add(m);
        }
        for (String pref : PREFERRED[providerIndex]) {
            for (String m : usable) if (m.toLowerCase(Locale.ROOT).contains(pref)) return m;
        }
        return usable.isEmpty() ? null : usable.get(0);
    }

    // ---------------------------------------------------------------- helpers
    private static String label(String p) {
        return Prefs.LABELS[Prefs.index(p)];
    }

    private static void check(Resp r, String label) throws AiException {
        if (r.code < 400) return;
        String msg = r.body;
        try {
            JSONObject j = new JSONObject(r.body);
            Object err = j.opt("error");
            if (err instanceof JSONObject) msg = ((JSONObject) err).optString("message", msg);
            else if (err instanceof String) msg = (String) err;
        } catch (Exception ignored) {
        }
        if (msg.length() > 200) msg = msg.substring(0, 200);
        String low = msg.toLowerCase(Locale.ROOT);
        if (r.code == 429) throw new AiException(label + ": rate limit reached, try again in a minute");
        if ((r.code == 401 || r.code == 403) && !low.contains("model")) throw new AiException(label + ": invalid API key");
        boolean gone = false;
        for (String h : GONE_HINTS) if (low.contains(h)) { gone = true; break; }
        if (r.code == 404 || ((r.code == 400 || r.code == 403) && low.contains("model") && gone)) {
            throw new ModelGone(label + ": model unavailable (" + msg + ")");
        }
        throw new AiException(label + ": error " + r.code + " – " + msg);
    }

    private static final class Resp {
        final int code; final String body;
        Resp(int code, String body) { this.code = code; this.body = body; }
    }

    private static Resp http(String method, String url, String json, String... headers) throws AiException {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setRequestMethod(method);
            c.setConnectTimeout(CONNECT_MS);
            c.setReadTimeout(READ_MS);
            c.setRequestProperty("Accept", "application/json");
            for (int i = 0; i + 1 < headers.length; i += 2) c.setRequestProperty(headers[i], headers[i + 1]);
            if (json != null) {
                c.setDoOutput(true);
                c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream os = c.getOutputStream()) {
                    os.write(json.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = c.getResponseCode();
            InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
            return new Resp(code, read(is));
        } catch (SocketTimeoutException e) {
            throw new AiException("The AI took too long to answer. Check your internet and try again.");
        } catch (java.io.IOException e) {
            throw new AiException("No internet connection (" + e.getClass().getSimpleName() + ")");
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String read(InputStream is) throws java.io.IOException {
        if (is == null) return "";
        try (InputStream in = is) {
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toString("UTF-8");
        }
    }

    private static final Pattern FENCE = Pattern.compile("^```[a-zA-Z]*\\n?|\\n?```$");
    private static final Pattern PREAMBLE = Pattern.compile(
            "^(here(?:'s| is) (?:the |your )?(?:fixed|corrected|rewritten|improved|reply)[^:\\n]*:)\\s*",
            Pattern.CASE_INSENSITIVE);

    /** Strip code fences, "Here is the fixed text:" and surrounding quotes. */
    static String clean(String text) {
        String t = text == null ? "" : text.trim();
        t = FENCE.matcher(t).replaceAll("").trim();
        Matcher m = PREAMBLE.matcher(t);
        if (m.find()) t = t.substring(m.end()).trim();
        String[][] pairs = {{"\"", "\""}, {"'", "'"}, {"“", "”"}, {"‘", "’"}, {"«", "»"}};
        for (int round = 0; round < 2; round++) {
            for (String[] q : pairs) {
                if (t.length() >= 2 && t.startsWith(q[0]) && t.endsWith(q[1]) && count(t, q[0]) <= 2) {
                    t = t.substring(q[0].length(), t.length() - q[1].length()).trim();
                }
            }
        }
        return t;
    }

    private static int count(String s, String sub) {
        int n = 0, i = 0;
        while ((i = s.indexOf(sub, i)) >= 0) { n++; i += sub.length(); }
        return n;
    }
}

package com.fixit.app;

import java.util.LinkedHashMap;
import java.util.Map;

/** Same prompts as the Windows app (config.py). */
final class Prompts {
    private Prompts() {}

    static final String DEFAULT_SYSTEM_PROMPT =
            "Fix grammar and make this sound natural and professional for a client. "
                    + "Keep my meaning and tone. Return only the fixed text.";

    static final String OUTPUT_RULES =
            "Rules: Do not add greetings, sign-offs, quotes, explanations, or markdown. "
                    + "Keep the same language as the input (unless asked to translate). "
                    + "Keep emojis, names, links and numbers unchanged. "
                    + "Output only the final text, nothing else.";

    static final String FIX = "Fix grammar";

    static final Map<String, String> MODES = new LinkedHashMap<>();
    static {
        MODES.put(FIX, DEFAULT_SYSTEM_PROMPT);
        MODES.put("More professional", "Rewrite this to sound more polished and professional for a client, "
                + "keeping my meaning. Return only the rewritten text.");
        MODES.put("Shorter", "Make this shorter and more concise while keeping the key meaning and "
                + "a natural, professional tone. Return only the rewritten text.");
        MODES.put("Friendlier", "Rewrite this to sound warmer and friendlier while staying professional. "
                + "Keep my meaning. Return only the rewritten text.");
        MODES.put("Bangla → English", "Translate this text from Bangla (it may be written in Bangla script or "
                + "romanized Banglish) into natural, professional English. Return only the English translation.");
    }

    static final String ALTERNATIVE_HINT = "\n\nThe user didn't like this previous version:\n<<<\n%s\n>>>\n"
            + "Write a clearly different alternative: use different words, a different opening and a different "
            + "sentence structure. Keep the same meaning, tone and rules. Do not repeat the previous version.";

    static final String REPLY_PROMPT =
            "You are helping me reply to a message I received (from a client, email, chat, etc.). "
                    + "Write a reply I can send, in first person, that is natural, clear and professional. "
                    + "Answer every question or point in the message. Do not invent facts, prices, dates or "
                    + "promises; if information is missing, use a short placeholder like [date]. "
                    + "Reply in the same language as the message. Return only the reply text, no subject "
                    + "line, no quotes, no markdown, no explanations.";

    static final String[] TONES = {"Professional", "Friendly", "Short", "Detailed", "Polite decline"};
    static final String[] TONE_HINTS = {
            "Tone: professional, clear and polite.",
            "Tone: warm and friendly, still professional.",
            "Keep it short: 1-3 sentences.",
            "Make it thorough and helpful, covering every point in detail.",
            "Politely decline the request while staying positive and professional.",
    };

    static String forMode(String mode, String customMain) {
        String base = FIX.equals(mode)
                ? (customMain == null || customMain.trim().isEmpty() ? DEFAULT_SYSTEM_PROMPT : customMain.trim())
                : MODES.get(mode);
        if (base == null) base = DEFAULT_SYSTEM_PROMPT;
        return base + "\n\n" + OUTPUT_RULES;
    }
}

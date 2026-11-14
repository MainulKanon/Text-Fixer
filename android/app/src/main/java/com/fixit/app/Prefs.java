package com.fixit.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Settings. API keys are encrypted with a key that lives in the Android Keystore
 * (hardware-backed on most phones), so they never sit on disk in plain text.
 */
final class Prefs {
    static final String[] PROVIDERS = {"groq", "gemini", "openrouter"};
    static final String[] LABELS = {"Groq", "Gemini", "OpenRouter"};
    static final String[] DEFAULT_MODELS = {"openai/gpt-oss-120b", "gemini-3.5-flash", "openai/gpt-oss-120b:free"};
    static final String[] KEY_URLS = {"https://console.groq.com/keys", "https://aistudio.google.com/app/apikey",
            "https://openrouter.ai/keys"};

    private static final String ALIAS = "fixit_api_keys";
    private final SharedPreferences sp;

    Prefs(Context c) {
        sp = c.getApplicationContext().getSharedPreferences("fixit", Context.MODE_PRIVATE);
    }

    static int index(String provider) {
        for (int i = 0; i < PROVIDERS.length; i++) if (PROVIDERS[i].equals(provider)) return i;
        return 0;
    }

    String key(String p) {
        String enc = sp.getString("key_" + p, "");
        if (enc.isEmpty()) return "";
        try {
            return decrypt(enc);
        } catch (Exception e) {
            return "";
        }
    }

    void setKey(String p, String value) {
        value = value == null ? "" : value.trim();
        try {
            sp.edit().putString("key_" + p, value.isEmpty() ? "" : encrypt(value)).apply();
        } catch (Exception e) {
            throw new IllegalStateException("Couldn't store the key securely: " + e.getMessage(), e);
        }
    }

    String model(String p) {
        String m = sp.getString("model_" + p, "");
        return m.isEmpty() ? DEFAULT_MODELS[index(p)] : m;
    }

    void setModel(String p, String m) {
        sp.edit().putString("model_" + p, m == null ? "" : m.trim()).apply();
    }

    /** Primary provider first, then the others in default order. */
    String[] order() {
        String primary = sp.getString("primary", "groq");
        String[] out = new String[PROVIDERS.length];
        out[0] = primary;
        int j = 1;
        for (String p : PROVIDERS) if (!p.equals(primary)) out[j++] = p;
        return out;
    }

    String primary() {
        return sp.getString("primary", "groq");
    }

    void setPrimary(String p) {
        sp.edit().putString("primary", p).apply();
    }

    String mainPrompt() {
        return sp.getString("main_prompt", Prompts.DEFAULT_SYSTEM_PROMPT);
    }

    void setMainPrompt(String s) {
        sp.edit().putString("main_prompt", s).apply();
    }

    boolean hasAnyKey() {
        for (String p : PROVIDERS) if (!key(p).isEmpty()) return true;
        return false;
    }

    // ---------- Keystore AES-GCM ----------
    private static SecretKey secretKey() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(ALIAS)) {
            return ((KeyStore.SecretKeyEntry) ks.getEntry(ALIAS, null)).getSecretKey();
        }
        KeyGenerator kg = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        kg.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return kg.generateKey();
    }

    private static String encrypt(String plain) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, secretKey());
        byte[] iv = c.getIV();
        byte[] ct = c.doFinal(plain.getBytes(StandardCharsets.UTF_8));
        byte[] all = new byte[iv.length + ct.length];
        System.arraycopy(iv, 0, all, 0, iv.length);
        System.arraycopy(ct, 0, all, iv.length, ct.length);
        return Base64.encodeToString(all, Base64.NO_WRAP);
    }

    private static String decrypt(String enc) throws Exception {
        byte[] all = Base64.decode(enc, Base64.NO_WRAP);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, secretKey(), new GCMParameterSpec(128, all, 0, 12));
        return new String(c.doFinal(all, 12, all.length - 12), StandardCharsets.UTF_8);
    }
}

package com.fixit.app;

import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.BackgroundColorSpan;
import android.text.style.ForegroundColorSpan;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** New text with inserted/changed words highlighted green (same idea as the desktop preview card). */
final class Diff {
    private Diff() {}

    // Android's regex engine doesn't support UNICODE_CHARACTER_CLASS, so spell out "word" characters with
    // Unicode categories (letters incl. Bangla, combining marks, digits).
    private static final Pattern TOKEN = Pattern.compile(
            "\\s+|[\\p{L}\\p{M}\\p{N}_]+|[^\\s\\p{L}\\p{M}\\p{N}_]");
    private static final int MAX_TOKENS = 600;   // keep the LCS table small (memory/CPU) on long texts

    static CharSequence highlight(String oldText, String newText, int bg, int fg) {
        List<String> a = tokens(oldText), b = tokens(newText);
        SpannableStringBuilder sb = new SpannableStringBuilder();
        if (a.size() > MAX_TOKENS || b.size() > MAX_TOKENS) return newText;
        int n = a.size(), m = b.size();
        int[][] lcs = new int[n + 1][m + 1];
        for (int i = n - 1; i >= 0; i--)
            for (int j = m - 1; j >= 0; j--)
                lcs[i][j] = a.get(i).equals(b.get(j)) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
        int i = 0, j = 0;
        while (j < m) {
            if (i < n && a.get(i).equals(b.get(j))) {
                sb.append(b.get(j));
                i++; j++;
            } else if (i < n && lcs[i + 1][j] >= lcs[i][j + 1]) {
                i++;                                   // word removed
            } else {
                String tok = b.get(j++);               // word added / changed
                int start = sb.length();
                sb.append(tok);
                if (!tok.trim().isEmpty()) {
                    sb.setSpan(new BackgroundColorSpan(bg), start, sb.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    sb.setSpan(new ForegroundColorSpan(fg), start, sb.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }
            }
        }
        return sb;
    }

    private static List<String> tokens(String s) {
        List<String> out = new ArrayList<>();
        Matcher mt = TOKEN.matcher(s);
        while (mt.find()) out.add(mt.group());
        return out;
    }
}

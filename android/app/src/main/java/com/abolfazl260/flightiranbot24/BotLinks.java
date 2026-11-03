package com.abolfazl260.flightiranbot24;

/** Fixed, public HTTPS destinations. No arbitrary URL or intent is accepted from untrusted input. */
public final class BotLinks {
    public static final String BOT = "https://t.me/Flightiranbot";
    // Telegram start payloads are allowlisted by start_handler in the bot.
    public static final String VISA = BOT + "?start=visa";
    public static final String AIRPORTS = BOT + "?start=airports";
    public static final String USEFUL = BOT + "?start=useful";
    public static final String SUPPORT = "https://t.me/Advertio_support";

    /** The route is encoded in a Telegram-approved, strictly bounded /start payload. */
    public static String visaWatch(String passport, String destination) {
        if (passport == null || destination == null ||
                !passport.matches("[A-Z]{2}") || !destination.matches("[A-Z]{2}")) {
            throw new IllegalArgumentException("Invalid visa country code");
        }
        return BOT + "?start=visa_" + passport + "_" + destination;
    }

    private BotLinks() {
    }
}

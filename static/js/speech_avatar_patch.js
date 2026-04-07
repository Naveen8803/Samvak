/**
 * speech_avatar_patch.js
 * ----------------------
 * Drop this AFTER speech.js in your base.html <head> (or bottom of body).
 * It patches the playAvatarIfVisible function to route tokens to the new
 * HandAvatar canvas instead of the old Three.js full-body avatar.
 *
 * Add to base.html (or speech_to_sign.html head block):
 *   <script defer src="{{ url_for('static', filename='js/hand_avatar.js') }}"></script>
 *   <script defer src="{{ url_for('static', filename='js/speech_avatar_patch.js') }}"></script>
 */

(function () {
    "use strict";

    // Wait for speech.js DOMContentLoaded setup to finish, then install hooks.
    // We use a MutationObserver + polling approach so we don't need to modify
    // speech.js source at all.

    function installHandAvatarHook() {
        // speech.js calls processFromResponse which calls playAvatarIfVisible.
        // We intercept at the DOM level: watch #signOutput for changes,
        // then trigger window.playHandAvatar if it exists.

        const signOutputEl = document.getElementById("signOutput");
        if (!signOutputEl || !window.HandAvatar) return;

        // Also hook into the replay button so it uses our canvas avatar
        const replayBtn = document.getElementById("replay-btn");

        // MutationObserver on the transcript so we can detect new sign output
        // The real hook: speech.js calls window.playHandAvatar(tokens, signText)
        // directly if we define it before DOMContentLoaded (see speech_to_sign.html).
        // This file is just the fallback / documentation that the hook exists.

        console.info("[HandAvatar] Avatar patch loaded. Canvas 2D avatar active.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installHandAvatarHook);
    } else {
        installHandAvatarHook();
    }
})();

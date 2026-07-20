/**
 * SAVE-108 — Renderer lifecycle coordinator (Phase F).
 *
 * Separate from SceneGraph, Diagnostics, and Bridge. Participants receive
 * initialize / activate / suspend / resume / shutdown notifications only
 * through this interface.
 */
(function(global)
{
    "use strict";

    function createRendererLifecycle()
    {
        const participants = [];
        let state = "created";

        function invoke(methodName)
        {
            for (const participant of participants)
            {
                const handler = participant[methodName];

                if (typeof handler === "function")
                    handler();
            }
        }

        function register(participant)
        {
            if (!participant || typeof participant !== "object")
                return;

            participants.push(participant);
        }

        function initialize()
        {
            if (state !== "created")
                return state;

            invoke("initialize");
            state = "initialized";
            return state;
        }

        function activate()
        {
            if (state === "created")
                initialize();

            if (state !== "initialized" && state !== "suspended")
                return state;

            invoke("activate");
            state = "active";
            return state;
        }

        function suspend()
        {
            if (state !== "active")
                return state;

            invoke("suspend");
            state = "suspended";
            return state;
        }

        function resume()
        {
            if (state !== "suspended")
                return state;

            invoke("resume");
            state = "active";
            return state;
        }

        function shutdown()
        {
            if (state === "shutdown")
                return state;

            invoke("shutdown");
            state = "shutdown";
            participants.length = 0;
            return state;
        }

        return {
            register: register,
            initialize: initialize,
            activate: activate,
            suspend: suspend,
            resume: resume,
            shutdown: shutdown,
            state: function() { return state; }
        };
    }

    global.createRendererLifecycle = createRendererLifecycle;
})(window);

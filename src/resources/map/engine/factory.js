/**
 * SAVE-108 — Map engine factory.
 *
 * Cesium is the sole production renderer (Phase F).
 */
(function(global)
{
    "use strict";

    function resolveEngineKind()
    {
        return "cesium";
    }

    function loadStylesheet(href)
    {
        return new Promise(function(resolve, reject)
        {
            if (document.querySelector("link[href=\"" + href + "\"]"))
            {
                resolve();
                return;
            }

            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            link.onload = function() { resolve(); };
            link.onerror = function()
            {
                reject(new Error("Failed to load stylesheet: " + href));
            };
            document.head.appendChild(link);
        });
    }

    function loadScript(src)
    {
        return new Promise(function(resolve, reject)
        {
            if (document.querySelector("script[src=\"" + src + "\"]"))
            {
                resolve();
                return;
            }

            const script = document.createElement("script");
            script.src = src;
            script.onload = function() { resolve(); };
            script.onerror = function()
            {
                reject(new Error("Failed to load script: " + src));
            };
            document.head.appendChild(script);
        });
    }

    async function ensureCesiumLoaded()
    {
        if (global.Cesium)
            return;

        global.CESIUM_BASE_URL = "cesium/";
        await loadStylesheet("cesium/Widgets/widgets.css");
        await loadScript("cesium/Cesium.js");
    }

    function createMapEngine()
    {
        if (typeof global.createCesiumEngine !== "function")
            throw new Error("Cesium map engine is not loaded.");

        return global.createCesiumEngine();
    }

    async function bootstrapMapEngine()
    {
        await ensureCesiumLoaded();

        const engine = createMapEngine();

        if (typeof global.installBridgeContract !== "function")
            throw new Error("Bridge contract is not loaded.");

        global.installBridgeContract(engine);

        const lifecycle = global.__rendererLifecycle
            || (typeof engine.getLifecycle === "function" ? engine.getLifecycle() : null);

        if (lifecycle)
        {
            lifecycle.initialize();
            lifecycle.activate();
        }

        return engine;
    }

    global.resolveMapEngineKind = resolveEngineKind;
    global.createMapEngine = createMapEngine;
    global.bootstrapMapEngine = bootstrapMapEngine;
})(window);

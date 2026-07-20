/**
 * SAVE-108 — IGlobeEngine bridge contract.
 *
 * Python calls the global entry points installed here. MapWidget must never
 * branch on renderer type; UI queries getRenderCapabilities() instead.
 */
(function(global)
{
    "use strict";

    const BRIDGE_VERSION = 1;

    /**
     * @typedef {Object} RenderCapabilities
     * @property {boolean} supports_globe
     * @property {boolean} supports_pitch
     * @property {boolean} supports_heading
     * @property {boolean} supports_geodesic
     * @property {boolean} supports_terrain
     * @property {string} engine_id
     */

    /** @type {RenderCapabilities} */
    const DEFAULT_CAPABILITIES = {
        supports_globe: false,
        supports_pitch: false,
        supports_heading: false,
        supports_geodesic: false,
        supports_terrain: false,
        engine_id: "unknown"
    };

    /**
     * Frozen bridge entry points (Python → JS).
     * @type {readonly string[]}
     */
    const BRIDGE_ENTRY_POINTS = [
        "updateShips",
        "removeShip",
        "clearShips",
        "updateObservationPoints",
        "clearObservationPoints",
        "beginLocationPick",
        "endLocationPick",
        "refreshLocationPickView",
        "enablePickMode",
        "setPickMode",
        "setPickOverlay",
        "setPickMarker",
        "clearPickMarker",
        "resetMapToWorldView",
        "focusShip",
        "clearObservationPoint",
        "setObservationPoint",
        "updateCameras",
        "clearCameras",
        "beginHeadingPick",
        "endHeadingPick",
        "setCameraPreview"
    ];

    /**
     * @typedef {Object} IGlobeEngine
     * @property {() => RenderCapabilities} getCapabilities
     * @property {(list: object[]) => void} updateShips
     * @property {(mmsi: number) => void} removeShip
     * @property {() => void} clearShips
     * @property {(points: object[]) => void} updateObservationPoints
     * @property {(message?: string) => void} clearObservationPoints
     * @property {(message?: string) => void} beginLocationPick
     * @property {() => void} endLocationPick
     * @property {(message?: string) => void} refreshLocationPickView
     * @property {(enabled: boolean) => void} enablePickMode
     * @property {(enabled: boolean) => void} setPickMode
     * @property {(message?: string) => void} setPickOverlay
     * @property {(lat: number, lon: number) => void} setPickMarker
     * @property {() => void} clearPickMarker
     * @property {() => void} resetMapToWorldView
     * @property {(mmsi: number) => void} focusShip
     */

    function defaultRendererDiagnostics()
    {
        return {
            fps: 0.0,
            frame_time_ms: 0.0,
            bridge_latency_ms: 0.0,
            entity_counts: {},
            memory_estimate: null,
            camera_state: {},
            transaction_queue_depth: 0
        };
    }

    /**
     * Install global bridge functions that delegate to the active engine.
     * @param {IGlobeEngine} engine
     */
    function installBridgeContract(engine)
    {
        const installedEntryPoints = [];

        for (const name of BRIDGE_ENTRY_POINTS)
        {
            if (typeof engine[name] !== "function")
                continue;

            installedEntryPoints.push(name);

            global[name] = ((methodName) => function(...args)
            {
                const start = performance.now();
                const result = engine[methodName](...args);

                if (
                    global.__rendererDiagnostics
                    && typeof global.__rendererDiagnostics.recordBridgeCall === "function"
                )
                {
                    global.__rendererDiagnostics.recordBridgeCall(start);
                }

                return result;
            })(name);
        }

        global.__mapEngine = engine;

        global.getRenderCapabilities = function()
        {
            if (engine && typeof engine.getCapabilities === "function")
                return engine.getCapabilities();

            return Object.assign({}, DEFAULT_CAPABILITIES);
        };

        global.getBridgeInfo = function()
        {
            const capabilities = global.getRenderCapabilities();

            return {
                version: BRIDGE_VERSION,
                engine: capabilities.engine_id || "unknown",
                capabilities: capabilities,
                entry_points: installedEntryPoints.slice()
            };
        };

        global.getRendererDiagnostics = function()
        {
            if (
                global.__rendererDiagnostics
                && typeof global.__rendererDiagnostics.snapshot === "function"
            )
            {
                return global.__rendererDiagnostics.snapshot();
            }

            return defaultRendererDiagnostics();
        };

        global.getRendererLifecycle = function()
        {
            if (global.__rendererLifecycle)
            {
                return {
                    state: global.__rendererLifecycle.state()
                };
            }

            return {
                state: "created"
            };
        };
    }

    global.BRIDGE_VERSION = BRIDGE_VERSION;
    global.DEFAULT_RENDER_CAPABILITIES = DEFAULT_CAPABILITIES;
    global.BRIDGE_ENTRY_POINTS = BRIDGE_ENTRY_POINTS;
    global.installBridgeContract = installBridgeContract;
})(window);

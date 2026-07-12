(function (global) {
    "use strict";

    var CONFIG_URL = "releases.json";

    function downloadUrl(platform, config) {
        var platformConfig = config[platform];
        if (!platformConfig || !platformConfig.file) {
            return "";
        }
        return "downloads/" + platform + "/" + encodeURIComponent(platformConfig.file);
    }

    function downloadFileUrl(platform, filename) {
        if (!filename) {
            return "";
        }
        return "downloads/" + platform + "/" + encodeURIComponent(filename);
    }

    function releaseNotesUrl(config) {
        return "releases/" + encodeURIComponent(config.latest) + ".md";
    }

    function loadConfig() {
        return fetch(CONFIG_URL, { cache: "no-store" }).then(function (response) {
            if (!response.ok) {
                throw new Error("Could not load releases.json (" + response.status + ")");
            }
            return response.json();
        });
    }

    function loadReleaseNotes(config) {
        return fetch(releaseNotesUrl(config), { cache: "no-store" }).then(function (response) {
            if (!response.ok) {
                throw new Error("Could not load release notes (" + response.status + ")");
            }
            return response.text();
        });
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderInlineMarkdown(text) {
        var html = escapeHtml(text);
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, label, url) {
            return '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
        });
        return html;
    }

    function renderMarkdown(markdown) {
        var lines = markdown.replace(/\r\n/g, "\n").split("\n");
        var html = [];
        var inList = false;

        function closeList() {
            if (inList) {
                html.push("</ul>");
                inList = false;
            }
        }

        lines.forEach(function (line) {
            var trimmed = line.trim();

            if (!trimmed) {
                closeList();
                return;
            }

            if (/^---+$/.test(trimmed)) {
                closeList();
                html.push("<hr>");
                return;
            }

            var headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/);
            if (headingMatch) {
                closeList();
                var level = headingMatch[1].length + 1;
                if (level > 4) {
                    level = 4;
                }
                html.push("<h" + level + ">" + renderInlineMarkdown(headingMatch[2]) + "</h" + level + ">");
                return;
            }

            if (/^[-*]\s+/.test(trimmed)) {
                if (!inList) {
                    html.push("<ul>");
                    inList = true;
                }
                html.push("<li>" + renderInlineMarkdown(trimmed.replace(/^[-*]\s+/, "")) + "</li>");
                return;
            }

            closeList();
            html.push("<p>" + renderInlineMarkdown(trimmed) + "</p>");
        });

        closeList();
        return html.join("\n");
    }

    function setText(selector, value) {
        document.querySelectorAll(selector).forEach(function (node) {
            node.textContent = value;
        });
    }

    function metaItem(label, value) {
        return '<li><span>' + escapeHtml(label) + "</span><strong>" + value + "</strong></li>";
    }

    function renderDownloadButton(platform, config, compact) {
        var platformConfig = config[platform];
        var href = downloadUrl(platform, config);
        var icon = platform === "windows" ? "🪟" : "🐧";
        var label =
            platform === "windows"
                ? "Download for Windows"
                : "Download .deb (recommended for Linux Mint)";

        return (
            '<a class="btn btn-primary btn-large" href="' +
            escapeHtml(href) +
            '" data-release-download="' +
            platform +
            '">' +
            '<span class="btn-icon" aria-hidden="true">' +
            icon +
            "</span> " +
            label +
            "</a>"
        );
    }

    function renderDownloadCard(platform, config, detailed) {
        var platformConfig = config[platform];
        var title = platform === "windows" ? "Windows" : "Linux";
        var description =
            platform === "windows"
                ? "Inno Setup installer for Windows 10 or later. Bundles PySide6, Qt WebEngine, offline Leaflet maps, and translations."
                : "Recommended for Linux Mint and Debian-based systems: install Project X from the .deb package for menu integration and clean uninstall. Use the portable AppImage only if you need a single file without system install.";

        var html =
            '<article class="panel download-card" data-release-platform="' +
            platform +
            '">' +
            "<h3>" +
            title +
            "</h3>" +
            "<p>" +
            description +
            "</p>";

        if (detailed) {
            html +=
                '<ul class="meta-list">' +
                metaItem("Version", escapeHtml(platformConfig.version)) +
                metaItem("Platform", escapeHtml(platformConfig.platform || title)) +
                metaItem("Recommended", escapeHtml(platformConfig.file)) +
                (platform === "linux" && platformConfig.secondary_file
                    ? metaItem("Portable option", escapeHtml(platformConfig.secondary_file))
                    : "") +
                metaItem("Format", escapeHtml(platformConfig.format || "")) +
                metaItem("Architecture", escapeHtml(platformConfig.architecture || "")) +
                metaItem("File size", escapeHtml(platformConfig.size || "TBD")) +
                "</ul>";
        }

        html += renderDownloadButton(platform, config, !detailed);

        if (platform === "linux" && platformConfig.secondary_file) {
            html +=
                '<p class="btn-row" style="margin-top: 0.75rem;">' +
                '<a class="btn btn-secondary" href="' +
                escapeHtml(downloadFileUrl("linux", platformConfig.secondary_file)) +
                '" data-release-download="linux-appimage">Download portable AppImage (advanced)</a>' +
                "</p>";
        }

        if (platformConfig.checksum_file) {
            html +=
                '<p class="note">Optional — verify download integrity: <a href="' +
                escapeHtml(downloadFileUrl(platform, platformConfig.checksum_file)) +
                '">' +
                escapeHtml(platformConfig.checksum_file) +
                "</a></p>";
        }

        if (detailed) {
            html +=
                '<p class="note">Recommended download: <code>' +
                escapeHtml(downloadUrl(platform, config)) +
                "</code></p>";
        }

        html += "</article>";
        return html;
    }

    function populateHome(config) {
        setText("[data-release-version]", config.latest);
        setText("[data-release-status]", config.status || "Release");
        setText("[data-release-notes-lead]", "Highlights from Project X " + config.latest + ".");

        var cards = document.querySelector("[data-release-download-cards]");
        if (cards) {
            cards.innerHTML = renderDownloadCard("windows", config, false) + renderDownloadCard("linux", config, false);
        }

        var notes = document.querySelector("[data-release-notes]");
        if (notes) {
            loadReleaseNotes(config)
                .then(function (markdown) {
                    notes.innerHTML = renderMarkdown(markdown);
                })
                .catch(function (error) {
                    notes.innerHTML = '<p class="note">' + escapeHtml(error.message) + "</p>";
                });
        }
    }

    function populateDownloadPage(config) {
        setText("[data-release-version]", config.latest);
        setText("[data-release-date]", config.release_date || "TBD");
        setText("[data-release-status]", config.status || "Release");

        var intro = document.querySelector("[data-release-intro]");
        if (intro) {
            intro.innerHTML =
                'Select your operating system. Latest version <strong>' +
                escapeHtml(config.latest) +
                "</strong> — " +
                escapeHtml((config.status || "release").toLowerCase()) +
                " for early adopters.";
        }

        var cards = document.querySelector("[data-release-download-cards]");
        if (cards) {
            cards.innerHTML = renderDownloadCard("windows", config, true) + renderDownloadCard("linux", config, true);
        }

        var meta = document.querySelector("[data-release-meta]");
        if (meta) {
            meta.innerHTML =
                metaItem("Latest version", escapeHtml(config.latest)) +
                metaItem("Release date", escapeHtml(config.release_date || "TBD")) +
                metaItem("Status", escapeHtml(config.status || "Release")) +
                metaItem(
                    "Source code",
                    '<a href="' +
                        escapeHtml(config.github || "https://github.com/Copex4590/ProjectX") +
                        '" target="_blank" rel="noopener noreferrer">github.com/Copex4590/ProjectX</a>'
                );
        }

        var notes = document.querySelector("[data-release-notes]");
        if (notes) {
            loadReleaseNotes(config)
                .then(function (markdown) {
                    notes.innerHTML = renderMarkdown(markdown);
                })
                .catch(function (error) {
                    notes.innerHTML = '<p class="note">' + escapeHtml(error.message) + "</p>";
                });
        }
    }

    function populateDocumentation(config) {
        setText("[data-release-version]", config.latest);
        setText("[data-release-date]", config.release_date || "TBD");

        var notes = document.querySelector("[data-release-notes]");
        if (notes) {
            loadReleaseNotes(config)
                .then(function (markdown) {
                    notes.innerHTML = renderMarkdown(markdown);
                })
                .catch(function (error) {
                    notes.innerHTML = '<p class="note">' + escapeHtml(error.message) + "</p>";
                });
        }
    }

    function init() {
        loadConfig()
            .then(function (config) {
                if (document.body.dataset.page === "home") {
                    populateHome(config);
                }
                if (document.body.dataset.page === "download") {
                    populateDownloadPage(config);
                }
                if (document.body.dataset.page === "documentation") {
                    populateDocumentation(config);
                }
            })
            .catch(function (error) {
                document.querySelectorAll("[data-release-error]").forEach(function (node) {
                    node.textContent = error.message;
                    node.hidden = false;
                });
            });
    }

    global.ProjectXReleases = {
        init: init,
        loadConfig: loadConfig,
        downloadUrl: downloadUrl,
        releaseNotesUrl: releaseNotesUrl,
        renderMarkdown: renderMarkdown
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})(window);

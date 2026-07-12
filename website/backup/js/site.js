(function () {
    "use strict";

    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".site-nav");

    if (toggle && nav) {
        toggle.addEventListener("click", function () {
            var isOpen = nav.classList.toggle("open");
            toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        nav.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                nav.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    var currentPage = document.body.dataset.page;
    if (currentPage) {
        document.querySelectorAll('.site-nav a[data-page="' + currentPage + '"]').forEach(function (link) {
            link.classList.add("active");
        });
    }
})();

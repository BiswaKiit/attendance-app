// Hide loader
window.addEventListener("load", function () {
    document.getElementById("loader").style.display = "none";
});

// Register service worker
if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js");
}
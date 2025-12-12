document.addEventListener("DOMContentLoaded", () => {
    const addForms = document.querySelectorAll(".add-to-list-form");
    const removeForms = document.querySelectorAll(".remove-from-list-form");
    const toastContainer = document.getElementById("toast-container");

    if (!toastContainer) return;

    // TOAST SYSTEM:
    function showToast(message, type = "info") {
        toastContainer.innerHTML = ""; // always keep only 1 toast

        const toast = document.createElement("div");
        toast.classList.add("toast", `toast-${type}`);
        toast.textContent = message;

        toastContainer.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add("show");
        });

        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 200);
        }, 2000);
    }

    // ADD TO THE LIST 
    addForms.forEach((form) => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });

                if (response.ok) {
                    showToast("Movie added to your list");
                } else {
                    showToast("Error adding movie", "error");
                }
            } catch (err) {
                console.error(err);
                showToast("Network error", "error");
            }
        });
    });

    // REMOVE MOVIE: 
    removeForms.forEach((form) => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const card = form.closest(".movie-card");
            if (!card) return;

            const formData = new FormData(form);

            // Instant fade out effect
            card.classList.add("fade-out");

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });

                if (response.ok) {
                    // this is for removing card after animation
                    setTimeout(() => card.remove(), 200);
                    showToast("Movie removed!");
                } else {
                    card.classList.remove("fade-out");
                    showToast("Error removing movie", "error");
                }
            } catch (err) {
                console.error(err);
                card.classList.remove("fade-out");
                showToast("Network error", "error");
            }
        });
    });
});

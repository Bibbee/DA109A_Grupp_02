document.addEventListener("DOMContentLoaded", () => {
    const forms = document.querySelectorAll(".add-to-list-form");
    const toast = document.getElementById("toast");

    if (!forms.length || !toast) return;

    forms.forEach((form) => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault(); 

            const formData = new FormData(form);

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                if (response.ok) {
                    showToast("Movie has been added to your list");
                } else {
                    showToast("Something went wrong, try again");
                }
            } catch (err) {
                console.error(err);
                showToast("Network error, try again");
            }
        });
    });

    function showToast(message) {
        toast.textContent = message;
        toast.classList.add("show");

        setTimeout(() => {
            toast.classList.remove("show");
        }, 2000); 
    }
});

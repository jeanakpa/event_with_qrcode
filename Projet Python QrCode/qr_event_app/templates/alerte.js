document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form[action="/generer_qr"]');
    const inputElement = form.querySelector('input[name="nom"]');
    const qrCodeContainer = document.getElementById('qrCodeContainer');
    const qrCodeImage = document.getElementById('qrCode');
    const message = document.getElementById('message'); 

    // Create a new element for the error message
    const errorElement = document.createElement('div');
    errorElement.className = 'text-xs text-red-500 mt-1';
    inputElement.parentNode.insertBefore(errorElement, inputElement.nextSibling);

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        fetch('/generer_qr', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                errorElement.textContent = data.error;
                message.textContent = "Déjà enregistré";
                qrCodeContainer.classList.add('hidden');
            } else {
                errorElement.textContent = ''; // Clear any previous error
                message.textContent = data.message || "Enregistrement réussi";
                qrCodeImage.src = data.qr_code;
                qrCodeContainer.classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            errorElement.textContent = "Une erreur est survenue lors de l'enregistrement.";
            qrCodeContainer.classList.add('hidden');
        });
    });
});
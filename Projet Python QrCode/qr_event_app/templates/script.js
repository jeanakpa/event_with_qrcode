// Ajoutez ce code à votre fichier script.js ou dans une balise <script> dans votre HTML

document.addEventListener('DOMContentLoaded', function() {
    const video = document.createElement('video');
    const canvasElement = document.createElement('canvas');
    const canvas = canvasElement.getContext('2d');
    const startScanButton = document.getElementById('startScan');
    const stopScanButton = document.getElementById('stopScan');
    const readerDiv = document.getElementById('reader');
    let scanning = false;

    startScanButton.addEventListener('click', startScan);
    stopScanButton.addEventListener('click', stopScan);

    function startScan() {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                .then(function(stream) {
                    scanning = true;
                    video.srcObject = stream;
                    video.setAttribute('playsinline', true);
                    video.play();
                    requestAnimationFrame(tick);
                    readerDiv.appendChild(video);
                    readerDiv.style.display = 'block';
                    startScanButton.style.display = 'none';
                    stopScanButton.style.display = 'inline-block';
                })
                .catch(function(error) {
                    console.error("Erreur d'accès à la caméra: ", error);
                    document.getElementById('resultat_scan').textContent = "Erreur d'accès à la caméra: " + error.message;
                });
        } else {
            console.error("getUserMedia n'est pas supporté sur ce navigateur");
            document.getElementById('resultat_scan').textContent = "La caméra n'est pas supportée sur ce navigateur";
        }
    }

    function stopScan() {
        scanning = false;
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
        readerDiv.style.display = 'none';
        startScanButton.style.display = 'inline-block';
        stopScanButton.style.display = 'none';
    }

    function tick() {
        if (video.readyState === video.HAVE_ENOUGH_DATA && scanning) {
            canvasElement.height = video.videoHeight;
            canvasElement.width = video.videoWidth;
            canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
            const imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
            
            // Ici, vous devriez intégrer une bibliothèque de lecture de QR code
            // Par exemple, avec jsQR :
            // const code = jsQR(imageData.data, imageData.width, imageData.height);
            // if (code) {
            //     console.log("QR Code détecté", code.data);
            //     // Traitez les données du QR code ici
            //     stopScan();
            // }
        }
        if (scanning) {
            requestAnimationFrame(tick);
        }
    }
});
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('scheduleForm').addEventListener('submit', async function (e) {
        e.preventDefault();

        const nameInput = document.getElementById('name');
        const gradeSelect = document.getElementById('grade');
        const scheduleImageInput = document.getElementById('scheduleImage');
        const nameError = document.getElementById('nameError');
        const resultDiv = document.getElementById('result');

        let valid = true;

        // Clear previous errors
        nameError.textContent = '';
        nameError.style.display = 'none';
        resultDiv.textContent = '';

        // Validate name
        if (nameInput.value.trim() === '') {
            nameError.textContent = 'Name is required';
            nameError.style.display = 'block';
            valid = false;
        }

        // Validate grade
        if (gradeSelect.value === '') {
            alert('Please select your grade');
            valid = false;
        }

        // Validate schedule image
        if (!scheduleImageInput.files.length) {
            alert('Please upload a schedule image');
            valid = false;
        }

        if (!valid) return;

        const formData = new FormData(document.getElementById('scheduleForm'));
        formData.append('name', nameInput.value);
        formData.append('grade', gradeSelect.value);
        formData.append('scheduleImage', scheduleImageInput.files[0]);

        try {
            const response = await fetch('/verify', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.location.href = '/verify';
            } else {
                const result = await response.json();
                resultDiv.innerText = result.message || 'An error occurred during submission';
            }
        } catch (error) {
            console.error('Error:', error);
            resultDiv.innerText = 'An error occurred during submission';
        }
    });
});

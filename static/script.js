document.getElementById('scheduleForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const nameInput = document.getElementById('name');
    const gradeSelect = document.getElementById('grade');
    const nameError = document.getElementById('nameError');

    let valid = true;

    if (nameInput.value.trim() === '') {
        nameError.textContent = 'Name is required';
        nameError.style.display = 'block';
        valid = false;
    } else {
        nameError.textContent = '';
        nameError.style.display = 'none';
    }

    if (gradeSelect.value === '') {
        alert('Please select your grade');
        valid = false;
    }

    if (!valid) return;

    const formData = new FormData();
    formData.append('name', nameInput.value);
    formData.append('grade', gradeSelect.value);
    formData.append('scheduleImage', document.getElementById('scheduleImage').files[0]);

    const response = await fetch('/upload', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
    document.getElementById('result').innerText = result.message;
});

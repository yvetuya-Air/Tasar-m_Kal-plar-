// Sunucu doğrulamasını tamamlayan, türe özgü form görünümü.
const bookType = document.getElementById('book_type');
function updateBookFields() {
  const physical = bookType.value === 'physical';
  for (const [id, active] of [['physical-fields', physical], ['ebook-fields', bookType.value === 'ebook'], ['upload-fields', !physical]]) {
    const field = document.getElementById(id);
    if (!field) continue;
    field.hidden = !active;
    for (const input of field.querySelectorAll('input')) input.disabled = !active;
    if (id === 'physical-fields') field.querySelector('input').required = physical;
    if (id === 'upload-fields') field.querySelector('input[type=file]').required = bookType.value === 'audio';
  }
}
if (bookType) {
  bookType.addEventListener('change', updateBookFields);
  updateBookFields();
}

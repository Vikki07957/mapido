document.querySelectorAll('form[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

const localDate = new Date();
const today = `${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, '0')}-${String(localDate.getDate()).padStart(2, '0')}`;
document.querySelectorAll('input[type="date"][min]').forEach((input) => {
  if (!input.value) input.min = today;
});

const messages = document.querySelector('#messages-list');
if (messages) messages.scrollTop = messages.scrollHeight;
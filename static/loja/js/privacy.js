document.addEventListener('DOMContentLoaded', function () {
    const deleteForm = document.querySelector('[data-confirm-delete]');
    if (deleteForm) deleteForm.addEventListener('submit', function (event) {
        if (!window.confirm('A anonimização remove os seus dados pessoais e encerra o acesso. Deseja continuar?')) event.preventDefault();
    });

    const deactivateForm = document.querySelector('[data-confirm-deactivate]');
    if (deactivateForm) deactivateForm.addEventListener('submit', function (event) {
        if (!window.confirm('O encerramento bloqueia o acesso à conta, mas mantém os dados para eventual reativação administrativa. Deseja continuar?')) event.preventDefault();
    });
});

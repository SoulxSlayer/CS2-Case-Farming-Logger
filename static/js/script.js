document.addEventListener('DOMContentLoaded', function() {

    // --- Edit Progress Modal Logic (Mostly stays the same) ---
    const editModal = document.getElementById('editProgressModal');
    if (editModal) {
        const editForm = document.getElementById('editProgressForm');
        const editAccountNameSpan = document.getElementById('editAccountName');
        const editWeekStartSpan = document.getElementById('editWeekStart');
        const editDropFarmedCheck = document.getElementById('edit_drop_farmed');
        const editCaseNameSelect = document.getElementById('edit_case_name');
        const editAdditionalDropInput = document.getElementById('edit_additional_drop');

        editModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget; // Button that triggered the modal
            if (!button.classList.contains('edit-btn')) return; // Ensure it's an edit button

            const progressId = button.getAttribute('data-progress-id');
            const accountName = button.getAttribute('data-account-name');
            const weekStart = button.getAttribute('data-week-start'); // This should be formatted YYYY-MM-DD
            const dropFarmed = button.getAttribute('data-drop-farmed') === 'true';
            const caseName = button.getAttribute('data-case-name');
            const additionalDrop = button.getAttribute('data-additional-drop');

            editForm.action = `/update_progress/${progressId}`;
            editAccountNameSpan.textContent = accountName;
            editWeekStartSpan.textContent = weekStart;
            editDropFarmedCheck.checked = dropFarmed;
            editCaseNameSelect.value = caseName || "";
            editAdditionalDropInput.value = additionalDrop || "";
        });
    }

    // --- Other Weeks Fetch Logic (MODIFY TO ADD EDIT BUTTONS) ---
    const fetchButton = document.getElementById('fetch-other-week');
    const otherWeekDateInput = document.getElementById('other_week_date');
    const otherWeekTbody = document.getElementById('other-week-tbody');
    const otherWeekError = document.getElementById('other-week-error');
    const otherWeekTfoot = document.getElementById('other-week-tfoot'); // Get the tfoot
const otherWeekTotalValueCell = document.getElementById('other-week-total-value'); // Get the cell for total

if (fetchButton && otherWeekDateInput && otherWeekTbody && otherWeekError && otherWeekTfoot && otherWeekTotalValueCell) {
        fetchButton.addEventListener('click', function() {
            const selectedDate = otherWeekDateInput.value;
            if (!selectedDate) {
                showError('Please select a date first.');
                return;
            }
            const dateObj = new Date(selectedDate + 'T00:00:00Z'); // Treat as UTC
            if (dateObj.getUTCDay() !== 3) {
                showError('Please select a Wednesday.');
                return;
            }

            hideError();
            otherWeekTbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>'; // Colspan 6
            otherWeekTfoot.style.display = 'none';

            fetch(`/get_week_data?date=${selectedDate}`)
                .then(response => {
                    if (!response.ok) {
                         return response.json().then(err => { throw new Error(err.error || `HTTP error! Status: ${response.status}`) });
                    }
                    return response.json();
                })
                .then(data => {
                    otherWeekTbody.innerHTML = ''; // Clear loading/previous data
                    otherWeekTbody.innerHTML = '';
                if (!data.progress || data.progress.length === 0) {
                    otherWeekTbody.innerHTML = '<tr><td colspan="6" class="text-center">No progress found for this week.</td></tr>'; // Colspan 6
                    otherWeekTfoot.style.display = 'none';
                } else {
                    data.progress.forEach(entry => {
                        const row = otherWeekTbody.insertRow();
                            const farmedText = entry.drop_farmed ? 'Yes' : 'No';
                            const caseNameText = entry.case_name || 'N/A';
                            const additionalDropText = entry.additional_drop || '-';
                            const accountLink = `<a href="https://steamcommunity.com/profiles/${entry.steamid}" target="_blank">${entry.account_name}</a>`;
                            const priceText = entry.case_value ? parseFloat(entry.case_value).toFixed(2) : '-';

                            let actionsCellContent = '<span class="text-muted fst-italic">-</span>';
                        if (entry.progress_id) {
                            actionsCellContent = `
                                <button class="btn btn-outline-info btn-sm edit-btn"
                                        data-bs-toggle="modal" data-bs-target="#editProgressModal"
                                        data-progress-id="${entry.progress_id}"
                                        data-account-name="${entry.account_name}"
                                        data-week-start="${entry.week_start}" 
                                        data-drop-farmed="${entry.drop_farmed ? 'true' : 'false'}"
                                        data-case-name="${entry.case_name || ''}"
                                        data-additional-drop="${entry.additional_drop || ''}">
                                    <i class="bi bi-pencil-square"></i> Edit
                                </button>
                            `;
                        }


                        row.innerHTML = `
                        <td>${accountLink}</td>
                        <td>${entry.drop_farmed ? 'Yes' : 'No'}</td>
                        <td>${entry.case_name || 'N/A'}</td>
                        <td>${entry.additional_drop || '-'}</td>
                        <td>${priceText}</td>
                        <td>${actionsCellContent}</td>
                    `;
                        });

                        // Display total value
                    otherWeekTotalValueCell.textContent = parseFloat(data.total_value).toFixed(2);
                    otherWeekTfoot.style.display = ''; // Show footer
                    }
                })
                .catch(error => {
                    console.error('Error fetching other week data:', error);
                    showError(`Failed to fetch data: ${error.message}`);
                     otherWeekTbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading data.</td></tr>'; // Colspan 5
                });
        });
    }

    function showError(message) { /* ... (no change) ... */ }
    function hideError() { /* ... (no change) ... */ }
});
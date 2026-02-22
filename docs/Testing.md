# Manual Sanity Test Checklist for Release

## Menu & Dishes

- [ ] Menu page loads without errors for all user roles
- [ ] All courses appear in the correct order as per menu ordering
- [ ] Dishes are grouped under the correct courses
- [ ] Adding a new dish works and it appears in the correct course
- [ ] Editing a dish updates its details and course correctly
- [ ] Deleting a dish removes it from the menu
- [ ] Changing course order and saving reflects immediately and after reload
- [ ] Dishes with no course are handled and displayed as expected

## Course Management

- [ ] Adding a new course works and it appears in the menu
- [ ] Editing a course name updates everywhere
- [ ] Deleting a course removes it and its dishes from the menu

## QR Code & Public Menu

- [ ] Downloading the public menu QR code works
- [ ] Public menu page loads and displays all dishes correctly

## Permissions & Access

- [ ] Only authorized users can add/edit/delete dishes and courses
- [ ] Unauthorized users cannot access admin features

## UI/UX

- [ ] Toast notifications appear for all actions (add, edit, delete, save order)
- [ ] Modal dialogs open and close as expected
- [ ] Drag-and-drop course ordering works smoothly

## API & Data

- [ ] API endpoints for courses and dishes return correct, ordered data
- [ ] No duplicate or missing dishes/courses in API responses

## Management Commands & Menu Import/Export

- [ ] All management commands run without errors (e.g., `python manage.py <command>`)
- [ ] Menu import command successfully imports menu data and updates the database
- [ ] Menu export command generates the correct output file with all menu data
- [ ] Importing a menu does not create duplicates or corrupt data
- [ ] Exported menu can be re-imported without issues
- [ ] Proper error messages are shown for invalid import files
- [ ] Permissions for running import/export commands are enforced as expected

## General

- [ ] No console errors in browser
- [ ] No server errors in logs during normal use
- [ ] All pages load within acceptable time

---
Update this checklist as features evolve.

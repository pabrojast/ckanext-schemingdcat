# Upload Snippets

This directory contains the modularized components of the upload form field template.

## Structure

The upload functionality has been split into separate files for better maintainability:

### `upload_base.html`
Main template file that serves as a reference. The actual `upload.html` in the parent directory includes these snippets.

### `upload_script.html` 
Contains all JavaScript functionality for the upload field (~2001 lines):
- File upload handling
- Drag and drop functionality
- MIME type detection
- Character set detection  
- Auto-fill of resource fields (name, format, created date, etc.)
- Format validation
- Spatial extent extraction integration
- Error handling and validation

### `upload_styles.html`
Contains all CSS styles for the upload field (~334 lines):
- Upload dropzone styling
- File preview styling
- Progress bar animations
- Responsive design
- Loading states
- Error states

## Usage

The main `upload.html` file includes these snippets using Jinja2's `{% include %}` directive:

```jinja2
<script>
  {% include 'schemingdcat/upload_snippets/upload_script.html' %}
</script>

<style>
  {% include 'schemingdcat/upload_snippets/upload_styles.html' %}
</style>
```

## Benefits

### Maintainability
- **Separation of Concerns**: HTML, JavaScript, and CSS in separate files
- **Easier Navigation**: Find specific functionality quickly
- **Better Testing**: Test JavaScript logic independently
- **Reduced Complexity**: No single file over 2400 lines

### Development
- **Focused Editing**: Work on JavaScript without seeing HTML/CSS
- **Code Review**: Easier to review changes in specific areas
- **Syntax Highlighting**: Better IDE support for each file type
- **Version Control**: Clearer diffs when files change

### Performance
- **Browser Caching**: (Future) Could potentially be served as static assets
- **Minification**: (Future) Easier to minify JavaScript and CSS separately

## File Sizes

| File | Lines | Content |
|------|-------|---------|
| upload.html (main) | ~100 | HTML structure + includes |
| upload_script.html | ~2001 | JavaScript functionality |
| upload_styles.html | ~334 | CSS styling |
| **Total** | **~2435** | Complete upload field |

## Original File

The original monolithic `upload.html` is backed up as `upload.html.bak` (2426 lines) for reference.

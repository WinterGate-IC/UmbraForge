"""Returning to saved work: paired project copies and the Saves menu."""

from __future__ import annotations

from umbraforge.layers import Design
from umbraforge.ui import dialogs


def test_a_flat_save_also_writes_the_editable_project(qapp, tmp_path,
                                                     monkeypatch):
    design = Design(name="Return To Me")
    dialog = dialogs.SaveDialog(design)
    try:
        target = tmp_path / "art.png"
        dialog.path_edit.setText(str(target))
        monkeypatch.setattr(dialogs.QMessageBox, "exec", lambda self: 0)
        dialog._save()

        assert dialog.saved_format == "png"
        assert target.exists()
        assert dialog.saved_project_path == tmp_path / "art.umbra"
        assert dialog.saved_project_path.exists()
        assert Design.open(dialog.saved_project_path).name == "Return To Me"
    finally:
        dialog.deleteLater()


def test_the_paired_copy_can_be_turned_off(qapp, tmp_path, monkeypatch):
    design = Design(name="Image Only")
    dialog = dialogs.SaveDialog(design)
    try:
        dialog.project_copy.setChecked(False)
        target = tmp_path / "flat.png"
        dialog.path_edit.setText(str(target))
        monkeypatch.setattr(dialogs.QMessageBox, "exec", lambda self: 0)
        dialog._save()

        assert target.exists()
        assert dialog.saved_project_path is None
        assert not (tmp_path / "flat.umbra").exists()
    finally:
        dialog.deleteLater()


def test_saves_menu_lists_recent_projects(window, tmp_path):
    design = Design(name="Night Work")
    path = design.save(tmp_path / "night-work.umbra")
    window._remember_project(path)

    labels = [action.text() for action in window.saves_menu.actions()]
    assert any("Continue where you left off" in label for label in labels)
    assert any("night-work" in label for label in labels)
    assert window._recent_paths()[0] == path.resolve()
    assert window.library_panel._resume_target == path.resolve()
    assert not window.library_panel._resume_button.isHidden()


def test_paired_project_overwrite_is_confirmed(qapp, tmp_path, monkeypatch):
    design = Design(name="Protect My Project")
    dialog = dialogs.SaveDialog(design)
    try:
        target = tmp_path / "art.png"
        paired = tmp_path / "art.umbra"
        paired.write_bytes(b"old editable project")
        seen: list[str] = []

        def question(_parent, _title, text, *args, **kwargs):
            seen.append(text)
            return dialogs.QMessageBox.StandardButton.Cancel

        monkeypatch.setattr(dialogs.QMessageBox, "question", question)
        dialog.path_edit.setText(str(target))
        dialog._save()

        assert len(seen) == 1
        assert "art.umbra" in seen[0]
        assert not target.exists()
        assert paired.read_bytes() == b"old editable project"
    finally:
        dialog.deleteLater()


def test_open_saves_folder_reports_a_failed_launch(window, tmp_path,
                                                   monkeypatch):
    from umbraforge import branding
    from umbraforge.ui import main_window

    folder = tmp_path / "saves"
    monkeypatch.setattr(branding, "saves_dir", lambda: folder)
    monkeypatch.setattr(main_window.QDesktopServices, "openUrl",
                        lambda _url: False)
    warnings: list[tuple] = []
    monkeypatch.setattr(main_window.QMessageBox, "warning",
                        lambda *args, **kwargs: warnings.append(args))

    window._open_saves_folder()

    assert folder.is_dir()
    assert warnings
    assert str(folder) in warnings[0][2]

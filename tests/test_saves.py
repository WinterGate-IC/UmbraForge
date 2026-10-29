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

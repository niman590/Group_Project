from flask import Blueprint, render_template, request, redirect, url_for, flash

gis_bp = Blueprint("gis", __name__, url_prefix="/gis")


@gis_bp.route("/mapping", methods=["GET"])
def gis_mapping_page():
    return render_template("gis_mapping.html", active_page="gis_map")


@gis_bp.route("/save-location", methods=["POST"])
def save_gis_location():
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    address = request.form.get("address")

    if not latitude or not longitude:
        flash("Please select a location on the map first.", "error")
        return redirect(url_for("gis.gis_mapping_page"))

    # Here you can save into database later
    # Example:
    # INSERT INTO property_locations (user_id, latitude, longitude, address) VALUES (...)

    flash("Location saved successfully.", "success")
    return redirect(url_for("gis.gis_mapping_page"))
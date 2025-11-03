import pandas, plotly.express as px, pycountry, sys

def country_alpha3(country_code):
    return pycountry.countries.get(alpha_2=country_code).alpha_3

dataframe = pandas.read_csv("log.csv", header=None, names=["ip","user","country","asn","time"])
dataframe["iso3"] = dataframe["country"].map(country_alpha3)
country_counts = dataframe.groupby("iso3").size().reset_index(name="count")

max_color_value = country_counts["count"].quantile(0.90)

figure = px.choropleth(
    country_counts,
    locations="iso3",
    color="count",
    color_continuous_scale=sys.argv[1],
    range_color=(0, max_color_value),
    projection="robinson",
    template="plotly_dark"
)

figure.update_geos(showcountries=True, showframe=True, showcoastlines=True)
figure.write_html("/var/www/tilley.lol/haxxors/index.html")

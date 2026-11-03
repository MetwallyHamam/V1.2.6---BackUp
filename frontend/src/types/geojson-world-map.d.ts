declare module "geojson-world-map/src/world.js" {
  import type { FeatureCollection, Geometry } from "geojson";
  const world: FeatureCollection<Geometry, { name?: string }>;
  export default world;
}

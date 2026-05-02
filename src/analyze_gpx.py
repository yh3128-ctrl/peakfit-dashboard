import os
import glob
import pandas as pd
import gpxpy
import math
from multiprocessing import Pool

# Haversine distance calculation
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def analyze_single_gpx(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
            
        mountain_name = os.path.basename(os.path.dirname(filepath))
        filename = os.path.basename(filepath)
        
        total_2d_distance = 0.0
        total_3d_distance = 0.0
        elevation_gain = 0.0
        min_ele = float('inf')
        max_ele = float('-inf')
        total_time_seconds = 0
        
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append(point)
                    
        if not points:
            return None
            
        start_time = points[0].time
        end_time = points[-1].time
        if start_time and end_time:
            total_time_seconds = (end_time - start_time).total_seconds()
            
        slopes = []
        for i in range(1, len(points)):
            p1 = points[i-1]
            p2 = points[i]
            
            # Elevation check
            e1 = p1.elevation if p1.elevation is not None else 0
            e2 = p2.elevation if p2.elevation is not None else 0
            
            min_ele = min(min_ele, e1, e2)
            max_ele = max(max_ele, e1, e2)
            
            ele_diff = e2 - e1
            if ele_diff > 0:
                elevation_gain += ele_diff
                
            dist_2d = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            dist_3d = math.sqrt(dist_2d**2 + ele_diff**2)
            
            total_2d_distance += dist_2d
            total_3d_distance += dist_3d
            
            if dist_2d > 0:
                slope = (abs(ele_diff) / dist_2d) * 100
                slopes.append(slope)
                
        avg_slope = sum(slopes) / len(slopes) if slopes else 0
        max_slope = max(slopes) if slopes else 0
        
        start_lat = points[0].latitude
        start_lon = points[0].longitude
        end_lat = points[-1].latitude
        end_lon = points[-1].longitude
        
        return {
            'Mountain': mountain_name,
            'Filename': filename,
            'Total_Distance_km': round(total_3d_distance / 1000, 2),
            'Elevation_Gain_m': round(elevation_gain, 2),
            'Min_Elevation_m': round(min_ele, 2) if min_ele != float('inf') else 0,
            'Max_Elevation_m': round(max_ele, 2) if max_ele != float('-inf') else 0,
            'Average_Slope_%': round(avg_slope, 2),
            'Max_Slope_%': round(max_slope, 2),
            'Estimated_Time_hrs': round(total_time_seconds / 3600, 2) if total_time_seconds > 0 else 0,
            'Start_Lat': start_lat,
            'Start_Lon': start_lon,
            'End_Lat': end_lat,
            'End_Lon': end_lon
        }
    except Exception as e:
        # Silently skip errors for this batch script
        return None

def main():
    base_dir = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\raw\100대명산"
    gpx_files = glob.glob(os.path.join(base_dir, "*", "*.gpx"))
    print(f"Found {len(gpx_files)} GPX files. Starting parallel processing...")
    
    with Pool() as pool:
        results = pool.map(analyze_single_gpx, gpx_files)
        
    valid_results = [r for r in results if r is not None]
    
    df = pd.DataFrame(valid_results)
    out_path = r"c:\Users\yh312\Downloads\icb8pjt2\tracking-pjt\data\processed\gpx_analysis_results.csv"
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Successfully processed {len(valid_results)} GPX files.")
    print(f"Results saved to: {out_path}")

if __name__ == '__main__':
    main()

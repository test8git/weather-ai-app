"use client";

import { useState } from "react";
import TemperatureChart from "@/components/TemperatureChart";
import { useLoading } from "@/context/LoadingContext"
import ChatBox from "@/components/ChatBox";


export default function Home() {

  const [city, setCity] = useState("");
  const [weather, setWeather] = useState(null);
  const { setGlobalLoading } = useLoading()
  const [error, setError] = useState("");

  const getWeather = async () => 
  {
    try
    {
      setWeather(null); 
      setGlobalLoading(true);
      setError("");

      if (!city.trim()) {
          alert("Please enter city name");
          return;
      }

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/weather?city=${city}`
      );

      if (!res.ok) {
        throw new Error("Failed to fetch weather");
      }

      const data = await res.json();

      setWeather(data);

    }
    catch (err)
    {

      setError(err.message);

    }
    finally
    {
      setGlobalLoading(false);
  }
};

  return (
    <div className="min-h-screen bg-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-4xl font-bold text-slate-800">
                Weather Dashboard
              </h1>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Enter city"
                className="border border-slate-300 rounded-xl px-4 py-3 w-64 outline-none focus:ring-2 focus:ring-blue-400"
                value={city} onChange={(e) => setCity(e.target.value)}
              />

              <button className="bg-blue-600 hover:bg-blue-700 text-white px-2 py-2 md:px-4  rounded-xl transition-all" onClick={getWeather}>
                Search
              </button>
            </div>            
          </div>

            {error && (
              <div>
                <p className="text-red-500 mt-4">
                  {error}
                </p>
              </div>
            )}
          
          {weather && (
          <div>  
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="bg-gradient-to-br from-blue-500 to-blue-700 text-white rounded-3xl p-6 shadow-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold">{weather.city}</h2>
                  </div>

                  <img
                    src={`https://openweathermap.org/img/wn/${weather.current_icon}@2x.png`}
                    alt={weather.current_condition}
                    className="w-24 h-24 object-contain"
                  />
                </div>

                <div className="mt-6">
                  <p className="text-6xl font-bold">{weather.current_temp}°C</p>
                  <p className="mt-2 opacity-80">{weather.current_condition}</p>
                </div>
              </div>

              <div className="bg-slate-50 rounded-3xl p-6 border border-slate-200">
                <h3 className="text-2xl font-bold text-slate-800 mb-4">
                  AI Weather Advice
                </h3>

                <div className="whitespace-pre-line text-slate-700 leading-7">
                  {weather.advice}
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-2xl font-bold text-slate-800 mb-6">
                Forecast
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
                {weather.forecast.map((item, index) => {
                  if(index <= 4)
                  {
                    return(
                    <div
                      key={index}
                      className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-lg transition-all"
                    >
                      <div className="text-sm text-slate-500 mb-3">
                        {new Date(item.date).toLocaleDateString("en-IN", {
                          weekday: "short",
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>

                      <img
                        src={`https://openweathermap.org/img/wn/${item.icon}@2x.png`}
                        alt={item.condition}
                        className="w-20 h-20 mx-auto object-contain"
                      />

                      <div className="text-center mt-2">
                        <p className="text-3xl font-bold text-slate-800">
                          {item.temp}°C
                        </p>

                        <p className="text-slate-500 mt-2">
                          {item.condition}
                        </p>
                      </div>
                  </div>
                    );
                }
                })}
              </div>
            </div>
            {/* <TemperatureChart forecast={weather.chart_data} /> */}
            <ChatBox city={city} forecast={weather.forecast} />
          </div>
          )}
        </div>
      </div>
    </div>
  );
}
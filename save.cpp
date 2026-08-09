#include <iostream>
#include <fstream>
#include <string>
#include <map>
#include <filesystem>
#include <thread>
#include <chrono>
using namespace std;

// Reads the save request file and converts the key=value pairs into a map
map<string, string> parseRequest(string filePath)
{
map<string, string> data;
ifstream file(filePath);
string line;

while (getline(file, line)){
    size_t position = line.find("=");
    if (position != string::npos){
        string key = line.substr(0, position);
        string value = line.substr(position + 1);

        data[key] = value;
    }
}

file.close();

return data;
}

// Creates a response file so the requesting program knows if the save worked
void writeResponse(string status, string fileName)
{
ofstream response("save_response.txt");
response << "status=" << status << endl;
if (status == "success"){
response << "file_saved=" << fileName << endl;
}
response.close();
}

// Saves the provided data into the requested user's file
void saveFileData(string username, string fileName, string data)
{
string path = username + "_" + fileName;
ofstream saveFile(path);
saveFile << data;
saveFile.close();
}

int main()
{
cout << "Save Service Running..." << endl;
string requestFile = "save_request.txt";

// Continuously checks for new save requests
while (true){
    if (filesystem::exists(requestFile)){
        cout << "Save request found!" << endl;

        // Read the request file and extract save information
        map<string, string> request = parseRequest(requestFile);

        // Check that the request contains the required parameters
        if (request.find("username") == request.end() || request.find("file_name") == request.end() || request.find("save_data") == request.end()){
            cout << "Invalid request." << endl;
            writeResponse("failure", "");
        }

        else{
            string username = request["username"];
            string fileName = request["file_name"];
            string saveData = request["save_data"];

            // Add username to file name so users only access their own saves
            string userFileName = username + "_" + fileName;

            // Save the data and send a response back
            saveFileData(username, fileName, saveData);
            writeResponse("success", userFileName);

            cout << "Saved: " << userFileName << endl;
        }
        
    // Remove the request so it is not processed again
    remove(requestFile.c_str());
    }

// Wait before checking for another request
this_thread::sleep_for(chrono::seconds(1));
}
}

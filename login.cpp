#include <iostream>
#include <fstream>
#include <string>
#include <map>
#include <filesystem>
#include <thread>
#include <chrono>

using namespace std;

// Reads key=value pairs from login_request.txt
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

// Checks username and password against users.txt
bool validateUser(string username, string password)
{
    ifstream users("users.txt");

    string line;

    while (getline(users, line)){
        size_t colon = line.find(":");

        if (colon != string::npos){
            string storedUser = line.substr(0, colon);
            string storedPass = line.substr(colon + 1);

            if (storedUser == username && storedPass == password){
                users.close();
                return true;
            }
        }
    }

    users.close();
    return false;
}

// Writes login_response.txt
void writeResponse(string status, string message, string username)
{
    ofstream response("login_response.txt");
    response << "status=" << status << endl;
    response << "message=" << message << endl;

    if(status == "success"){
        response << "username=" << username << endl;
    }

    response.close();
}

int main()
{
    cout << "Login Service Running..." << endl;

    string requestFile = "login_request.txt";

    while (true){
        if (filesystem::exists(requestFile)){
            cout << "Login request found!" << endl;

            map<string, string> request = parseRequest(requestFile);

            if (request.find("username") == request.end() || request.find("password") == request.end()){
                cout << "Invalid request." << endl;
                writeResponse("failure", "Invalid request format", "");
            }

            else{
                string username = request["username"];
                string password = request["password"];

                if (validateUser(username, password)){
                    writeResponse("success", "Login successful", username);
                    cout << username << " logged in successfully." << endl;
                }

                else{
                    writeResponse("failure", "Invalid username or password", "");
                    cout << "Login failed." << endl;
                }
            }

            remove(requestFile.c_str());
        }

        this_thread::sleep_for(chrono::seconds(1));
    }
}

#include<iostream>
#include<vector>
#include<fstream>

using namespace std;

int n,s;
bool avable[200];
double rate[200][200];
vector<int> path;

double exchg(double have,int u,int v)
{
    return have*rate[u][v];
}

int dfs(int p,double have)
{
    int i;
//    cout<<p<<" "<<have<<endl;
    path.push_back(p);
    if(exchg(have,p,s)>100.1)
    {
        for(i=0;i<path.size();i++)
          cout<<path[i]<<" ";
        cout<<exchg(have,p,s)<<endl;
        path.pop_back();
        avable[p]=1;
        return 1;
    }
    avable[p]=0;
    for(i=1;i<=n;i++)
        if(avable[i]) dfs(i,exchg(have,p,i));
    avable[p]=1;
    path.pop_back();
    return 0;
}

int main()
{
    ifstream fin("data.txt");
    fin>>n>>s;
    int i,j;
    for(i=1;i<=n;i++)
        for(j=1;j<=n;j++)
          fin>>rate[i][j];
    for(i=1;i<=n;i++)
        avable[i]=1;
    dfs(s,100);
    return 0;
}